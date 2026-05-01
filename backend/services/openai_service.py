import re

from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.prompts.ocr_prompts import build_ocr_prompt


class OCROutput(BaseModel):
    """Structured output for OCR results."""
    markdown: str


class OpenAIService:
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
        """Process a single image with OpenAI Vision API using structured output."""
        prompt = build_ocr_prompt(contains_latex, contains_diagrams, custom_instructions)

        response = await self.client.beta.chat.completions.parse(
            model="gpt-4o",
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

        # Get the parsed markdown
        result = response.choices[0].message.parsed
        markdown = result.markdown if result else ""

        # Clean up any remaining code fences just in case
        markdown = self._clean_markdown(markdown)

        return markdown

    def _clean_markdown(self, text: str) -> str:
        """Remove any markdown code fences that wrap the entire content."""
        # Remove ```markdown ... ``` wrapping
        text = re.sub(r'^```(?:markdown)?\s*\n?', '', text.strip())
        text = re.sub(r'\n?```\s*$', '', text.strip())
        return text.strip()
