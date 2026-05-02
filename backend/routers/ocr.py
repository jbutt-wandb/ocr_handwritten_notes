import base64
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import settings
from backend.services.credentials import store as credential_store
from backend.services.providers import (
    SUPPORTED_PROVIDERS,
    ProviderError,
    ProviderNotConfigured,
    get_provider,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR"])


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


@router.post("/process", response_model=OCRResponse)
async def process_images(
    images: Annotated[list[UploadFile], File()],
    contains_latex: Annotated[bool, Form()] = False,
    contains_diagrams: Annotated[bool, Form()] = False,
    custom_instructions: Annotated[str, Form()] = "",
    provider: Annotated[str, Form()] = "openai",
):
    """Process uploaded images with OCR using the selected provider."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_provider",
                "message": f"Provider must be one of {SUPPORTED_PROVIDERS}, got '{provider}'.",
            },
        )

    try:
        ocr_provider = get_provider(provider, credential_store)
    except ProviderNotConfigured:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "provider_not_configured",
                "message": f"No API key configured for {provider}. Add one via the credentials modal.",
            },
        )

    logger.info(f"=== Starting OCR processing (provider={provider}) ===")
    logger.info(f"Number of images: {len(images)}")
    logger.info(f"Options - LaTeX: {contains_latex}, Diagrams: {contains_diagrams}")
    if custom_instructions:
        logger.info(f"Custom instructions: {custom_instructions[:100]}...")

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
            logger.info(f"Sending image to {provider}...")
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            markdown = await ocr_provider.process_image(
                image_base64, mime_type, contains_latex, contains_diagrams, custom_instructions
            )
            logger.info(f"Received response for image {index + 1} ({len(markdown)} chars)")

            results.append(
                OCRResult(
                    image_index=index,
                    filename=image.filename or f"image_{index}",
                    markdown=markdown,
                )
            )
        except ProviderError as e:
            logger.error(f"{provider} returned {e.status_code} for image {index + 1}: {e.message}")
            raise HTTPException(
                status_code=e.status_code,
                detail={"code": e.code, "message": e.message},
            )
        except Exception as e:
            logger.error(f"OCR processing failed for image {index + 1}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={"code": "ocr_failed", "message": str(e)},
            )

    logger.info(f"=== OCR processing complete. Processed {len(results)} images ===")
    return OCRResponse(success=True, results=results)
