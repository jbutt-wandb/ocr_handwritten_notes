import base64
import logging
from typing import Annotated

import weave
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel

from backend.config import settings
from backend.services.credentials import store as credential_store
from backend.services.inference_service import InferenceService
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


@weave.op(name="process_ocr_request")
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
