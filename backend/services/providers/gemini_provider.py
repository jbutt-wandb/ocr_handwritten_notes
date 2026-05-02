import base64

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from backend.prompts.ocr_prompts import build_ocr_prompt
from backend.services.providers.base import (
    OCROutput,
    OCRProvider,
    ProviderError,
    ProviderUnreachableError,
    clean_markdown,
)

MODEL = "gemini-2.5-pro"


class GeminiProvider(OCRProvider):
    name = "gemini"

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def process_image(
        self,
        image_base64: str,
        mime_type: str,
        contains_latex: bool,
        contains_diagrams: bool,
        custom_instructions: str = "",
    ) -> str:
        prompt = build_ocr_prompt(contains_latex, contains_diagrams, custom_instructions)
        image_bytes = base64.b64decode(image_base64)
        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=OCROutput,
                    max_output_tokens=4096,
                ),
            )
        except genai_errors.ClientError as e:
            status = getattr(e, "code", None) or getattr(e, "status_code", None) or 400
            raise ProviderError(str(e), status_code=int(status), code="gemini_error") from e
        except genai_errors.ServerError as e:
            raise ProviderUnreachableError(f"Gemini server error: {e}") from e
        except genai_errors.APIError as e:
            raise ProviderError(str(e), status_code=502, code="gemini_error") from e

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, OCROutput):
            markdown = parsed.markdown
        elif isinstance(parsed, dict):
            markdown = parsed.get("markdown", "") or ""
        else:
            markdown = getattr(response, "text", "") or ""

        return clean_markdown(markdown)
