import anthropic
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AsyncAnthropic

from backend.prompts.ocr_prompts import build_ocr_prompt
from backend.services.providers.base import (
    OCRProvider,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnreachableError,
    clean_markdown,
)

MODEL = "claude-sonnet-4-6"
TOOL_NAME = "extract_markdown"

EXTRACT_TOOL = {
    "name": TOOL_NAME,
    "description": "Return the transcribed handwritten notes as clean Markdown.",
    "input_schema": {
        "type": "object",
        "properties": {
            "markdown": {
                "type": "string",
                "description": "Full transcribed Markdown content, no preamble or code fences.",
            }
        },
        "required": ["markdown"],
    },
}


class AnthropicProvider(OCRProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key, timeout=60.0)

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
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=[EXTRACT_TOOL],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_base64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"Anthropic timed out: {e}") from e
        except APIConnectionError as e:
            raise ProviderUnreachableError(f"Could not reach Anthropic: {e}") from e
        except APIStatusError as e:
            msg = getattr(e, "message", None) or str(e)
            raise ProviderError(msg, status_code=e.status_code, code="anthropic_error") from e
        except anthropic.AnthropicError as e:
            raise ProviderError(str(e), status_code=502, code="anthropic_error") from e

        markdown = ""
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
                markdown = (block.input or {}).get("markdown", "")
                break

        return clean_markdown(markdown)
