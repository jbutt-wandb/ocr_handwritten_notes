from mistralai import Mistral

from backend.prompts.ocr_prompts import build_ocr_prompt
from backend.services.providers.base import (
    OCRProvider,
    ProviderError,
    clean_markdown,
)

MODEL = "mistral-medium-latest"


class MistralProvider(OCRProvider):
    name = "mistral"

    def __init__(self, api_key: str):
        self.client = Mistral(api_key=api_key)

    async def process_image(
        self,
        image_base64: str,
        mime_type: str,
        contains_latex: bool,
        contains_diagrams: bool,
        custom_instructions: str = "",
    ) -> str:
        prompt = build_ocr_prompt(contains_latex, contains_diagrams, custom_instructions)
        try:
            response = await self.client.chat.complete_async(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": f"data:{mime_type};base64,{image_base64}",
                            },
                        ],
                    }
                ],
                max_tokens=4096,
            )
        except Exception as e:
            # Mistral's SDK raises mistralai.models.SDKError (with .status_code); a broad
            # catch keeps us robust across SDK versions, mirroring the Gemini provider.
            status = getattr(e, "status_code", None) or 502
            message = getattr(e, "message", None) or str(e)
            raise ProviderError(message, status_code=int(status), code="mistral_error") from e

        markdown = response.choices[0].message.content or ""
        # Vision responses are plain strings, but guard against list-of-parts shapes.
        if isinstance(markdown, list):
            markdown = "".join(
                part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
                for part in markdown
            )
        return clean_markdown(markdown)
