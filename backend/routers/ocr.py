import asyncio
import base64
import hashlib
import logging
from typing import Annotated, Optional

import weave
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel

from backend.config import settings
from backend.services.credentials import store as credential_store
from backend.services.inference_service import AVAILABLE_MODELS, InferenceService
from backend.services.scorers import get_injection_scorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


def get_inference_service() -> InferenceService:
    creds = credential_store.get()
    if not (creds.wandb_api_key and creds.weave_entity and creds.weave_project):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "wandb_not_configured",
                "message": "W&B credentials are not set. Open the credentials modal to add your W&B API key, entity, and project.",
            },
        )
    return InferenceService(
        api_key=creds.wandb_api_key,
        entity=creds.weave_entity,
        project=creds.weave_project,
        model=creds.model,
    )


class OCRResult(BaseModel):
    image_index: int
    filename: str
    markdown: str


class OCRResponse(BaseModel):
    success: bool
    results: list[OCRResult] = []
    error: str | None = None


MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


def _process_inputs_for_trace(inputs: dict) -> dict:
    return {
        "image_count": len(inputs.get("images") or []),
        "contains_latex": inputs.get("contains_latex"),
        "contains_diagrams": inputs.get("contains_diagrams"),
        "custom_instructions": inputs.get("custom_instructions", ""),
    }


def _process_output_for_trace(response: "OCRResponse") -> list[str]:
    return [r.markdown for r in response.results]


def _compare_inputs_for_trace(inputs: dict) -> dict:
    b64 = inputs.get("image_base64") or ""
    return {
        "image_size_kb": round(len(b64) * 3 / 4 / 1024, 1),
        "image_sha256": hashlib.sha256(b64.encode()).hexdigest()[:16],
        "contains_latex": inputs.get("contains_latex"),
        "contains_diagrams": inputs.get("contains_diagrams"),
        "custom_instructions": inputs.get("custom_instructions", ""),
    }


def _compare_output_for_trace(response: "ComparisonResponse") -> list[dict]:
    return [{"model_id": r.model_id, "markdown": r.markdown} for r in response.results]


@weave.op(name="preflight_custom_instructions")
def preflight_custom_instructions(custom_instructions: str) -> str:
    return custom_instructions


async def _check_prompt_injection(custom_instructions: str) -> None:
    if not custom_instructions or not custom_instructions.strip():
        return

    _, preflight_call = preflight_custom_instructions.call(custom_instructions)
    scorer = get_injection_scorer()
    apply_result = await preflight_call.apply_scorer(scorer)
    verdict = apply_result.result

    if not verdict.get("passed", True):
        logger.warning(
            "Prompt injection detected (risk=%.3f) — rejecting request",
            verdict.get("risk_score", 0.0),
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "prompt_injection_detected",
                "message": (
                    "Custom instructions appear to contain a prompt-injection "
                    "attempt. Edit and retry."
                ),
                "risk_score": verdict.get("risk_score", 0.0),
            },
        )


@weave.op(
    name="process_ocr_request",
    postprocess_inputs=_process_inputs_for_trace,
    postprocess_output=_process_output_for_trace,
)
async def _traced_process_ocr_request(
    images: list[UploadFile],
    contains_latex: bool,
    contains_diagrams: bool,
    custom_instructions: str,
    inference_service: InferenceService,
) -> OCRResponse:
    with weave.attributes(
        {
            "endpoint": "ocr.process",
            "image_count": len(images),
            "contains_latex": contains_latex,
            "contains_diagrams": contains_diagrams,
            "custom_instructions_present": bool(
                custom_instructions and custom_instructions.strip()
            ),
        }
    ):
        await _check_prompt_injection(custom_instructions)

        results = []

        for index, image in enumerate(images):
            logger.info(f"Processing image {index + 1}/{len(images)}: {image.filename}")

            ext = image.filename.split(".")[-1].lower() if image.filename else ""
            if ext not in settings.allowed_extensions:
                logger.error(f"Invalid file type: {ext}")
                raise HTTPException(
                    status_code=400, detail=f"Invalid file type: {ext}"
                )

            mime_type = MIME_TYPES.get(ext, "image/jpeg")

            image_bytes = await image.read()
            logger.info(f"Image size: {len(image_bytes) / 1024:.1f} KB")

            if len(image_bytes) > settings.max_file_size_mb * 1024 * 1024:
                logger.error(f"File {image.filename} exceeds size limit")
                raise HTTPException(
                    status_code=400,
                    detail=f"File {image.filename} exceeds {settings.max_file_size_mb}MB limit",
                )

            try:
                logger.info(f"Sending image to W&B Inference...")
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                markdown = await inference_service.process_image(
                    image_base64,
                    mime_type,
                    contains_latex,
                    contains_diagrams,
                    custom_instructions,
                )
                logger.info(f"Received response for image {index + 1} ({len(markdown)} chars)")

                results.append(
                    OCRResult(
                        image_index=index,
                        filename=image.filename or f"image_{index}",
                        markdown=markdown,
                    )
                )
            except APIStatusError as e:
                msg = getattr(e, "message", None) or str(e)
                logger.error(f"W&B Inference returned {e.status_code} for image {index + 1}: {msg}")
                raise HTTPException(
                    status_code=e.status_code,
                    detail={"code": "inference_error", "message": msg},
                )
            except APITimeoutError as e:
                logger.error(f"W&B Inference timeout for image {index + 1}: {e}")
                raise HTTPException(
                    status_code=504,
                    detail={"code": "inference_timeout", "message": f"W&B Inference timed out: {e}"},
                )
            except APIConnectionError as e:
                logger.error(f"W&B Inference unreachable for image {index + 1}: {e}")
                raise HTTPException(
                    status_code=502,
                    detail={"code": "inference_unreachable", "message": f"Could not reach W&B Inference: {e}"},
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"OCR processing failed for image {index + 1}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail={"code": "ocr_failed", "message": str(e)},
                )

        return OCRResponse(success=True, results=results)


@router.post("/process", response_model=OCRResponse)
async def process_images(
    images: Annotated[list[UploadFile], File()],
    contains_latex: Annotated[bool, Form()] = False,
    contains_diagrams: Annotated[bool, Form()] = False,
    custom_instructions: Annotated[str, Form()] = "",
    inference_service: InferenceService = Depends(get_inference_service),
):
    logger.info(f"=== Starting OCR processing ===")
    logger.info(f"Number of images: {len(images)}")
    logger.info(f"Options - LaTeX: {contains_latex}, Diagrams: {contains_diagrams}")
    if custom_instructions:
        logger.info(f"Custom instructions: {custom_instructions[:100]}...")

    response = await _traced_process_ocr_request(
        images=images,
        contains_latex=contains_latex,
        contains_diagrams=contains_diagrams,
        custom_instructions=custom_instructions,
        inference_service=inference_service,
    )

    logger.info(f"=== OCR processing complete. Processed {len(response.results)} images ===")
    return response


# ---------------------------------------------------------------------------
# Comparison endpoint — runs every available model on a single image so the
# user can pick which one fits their handwriting best.
# ---------------------------------------------------------------------------


class ComparisonResult(BaseModel):
    model_id: str
    model_label: str
    markdown: Optional[str] = None
    error: Optional[str] = None


class ComparisonResponse(BaseModel):
    success: bool
    filename: str
    results: list[ComparisonResult] = []


async def _run_one_model(
    *,
    model_id: str,
    model_label: str,
    api_key: str,
    entity: Optional[str],
    project: Optional[str],
    image_base64: str,
    mime_type: str,
    contains_latex: bool,
    contains_diagrams: bool,
    custom_instructions: str,
) -> ComparisonResult:
    """Run a single model and capture its outcome as a ComparisonResult.

    Per-model failures are returned as ``error`` so a single bad model
    doesn't kill the whole comparison run.
    """
    try:
        service = InferenceService(
            api_key=api_key, entity=entity, project=project, model=model_id
        )
        with weave.attributes({"model_id": model_id, "comparison_child": True}):
            markdown = await service.process_image(
                image_base64,
                mime_type,
                contains_latex,
                contains_diagrams,
                custom_instructions,
            )
        return ComparisonResult(
            model_id=model_id, model_label=model_label, markdown=markdown
        )
    except APIStatusError as e:
        msg = getattr(e, "message", None) or str(e)
        logger.error(f"[compare] {model_id} returned {e.status_code}: {msg}")
        return ComparisonResult(model_id=model_id, model_label=model_label, error=msg)
    except APITimeoutError as e:
        logger.error(f"[compare] {model_id} timed out: {e}")
        return ComparisonResult(
            model_id=model_id, model_label=model_label, error=f"Timed out: {e}"
        )
    except APIConnectionError as e:
        logger.error(f"[compare] {model_id} unreachable: {e}")
        return ComparisonResult(
            model_id=model_id, model_label=model_label, error=f"Could not reach W&B Inference: {e}"
        )
    except Exception as e:
        logger.error(f"[compare] {model_id} failed: {e}")
        return ComparisonResult(
            model_id=model_id, model_label=model_label, error=str(e)
        )


@weave.op(
    name="process_ocr_comparison",
    postprocess_inputs=_compare_inputs_for_trace,
    postprocess_output=_compare_output_for_trace,
)
async def _traced_process_ocr_comparison(
    image_base64: str,
    mime_type: str,
    filename: str,
    contains_latex: bool,
    contains_diagrams: bool,
    custom_instructions: str,
    api_key: str,
    entity: Optional[str],
    project: Optional[str],
) -> ComparisonResponse:
    with weave.attributes(
        {
            "endpoint": "ocr.compare",
            "model_count": len(AVAILABLE_MODELS),
            "filename": filename,
            "contains_latex": contains_latex,
            "contains_diagrams": contains_diagrams,
            "custom_instructions_present": bool(
                custom_instructions and custom_instructions.strip()
            ),
        }
    ):
        await _check_prompt_injection(custom_instructions)

        tasks = [
            _run_one_model(
                model_id=model_id,
                model_label=model_label,
                api_key=api_key,
                entity=entity,
                project=project,
                image_base64=image_base64,
                mime_type=mime_type,
                contains_latex=contains_latex,
                contains_diagrams=contains_diagrams,
                custom_instructions=custom_instructions,
            )
            for model_id, model_label in AVAILABLE_MODELS.items()
        ]

        results = await asyncio.gather(*tasks)
        return ComparisonResponse(success=True, filename=filename, results=results)


@router.post("/compare", response_model=ComparisonResponse)
async def compare_models(
    image: Annotated[UploadFile, File()],
    contains_latex: Annotated[bool, Form()] = False,
    contains_diagrams: Annotated[bool, Form()] = False,
    custom_instructions: Annotated[str, Form()] = "",
    inference_service: InferenceService = Depends(get_inference_service),
):
    """Run every available W&B vision model on a single image in parallel."""
    logger.info("=== Starting OCR comparison ===")
    logger.info(f"Models: {list(AVAILABLE_MODELS.keys())}")
    logger.info(f"Options - LaTeX: {contains_latex}, Diagrams: {contains_diagrams}")

    ext = image.filename.split(".")[-1].lower() if image.filename else ""
    if ext not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {ext}")

    mime_type = MIME_TYPES.get(ext, "image/jpeg")
    image_bytes = await image.read()

    if len(image_bytes) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File {image.filename} exceeds {settings.max_file_size_mb}MB limit",
        )

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    creds = credential_store.get()
    response = await _traced_process_ocr_comparison(
        image_base64=image_base64,
        mime_type=mime_type,
        filename=image.filename or "image",
        contains_latex=contains_latex,
        contains_diagrams=contains_diagrams,
        custom_instructions=custom_instructions,
        api_key=creds.wandb_api_key,
        entity=creds.weave_entity,
        project=creds.weave_project,
    )

    succeeded = sum(1 for r in response.results if r.markdown)
    failed = len(response.results) - succeeded
    logger.info(f"=== OCR comparison complete. {succeeded} ok, {failed} failed ===")
    return response
