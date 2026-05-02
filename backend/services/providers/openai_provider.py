from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from backend.prompts.ocr_prompts import build_ocr_prompt
from backend.services.providers.base import (
    OCROutput,
    OCRProvider,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnreachableError,
    clean_markdown,
)

MODEL = "gpt-4o"


class OpenAIProvider(OCRProvider):
    name = "openai"

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key, timeout=60.0)

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
            response = await self.client.beta.chat.completions.parse(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                response_format=OCROutput,
                max_tokens=4096,
            )
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"OpenAI timed out: {e}") from e
        except APIConnectionError as e:
            raise ProviderUnreachableError(f"Could not reach OpenAI: {e}") from e
        except APIStatusError as e:
            msg = getattr(e, "message", None) or str(e)
            raise ProviderError(msg, status_code=e.status_code, code="openai_error") from e

        result = response.choices[0].message.parsed
        markdown = result.markdown if result else ""
        return clean_markdown(markdown)
