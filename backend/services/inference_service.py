import base64
import io
import logging
import re
import time
from typing import Optional

import weave
from openai import AsyncOpenAI
from PIL import Image
from pydantic import BaseModel

from backend.prompts.ocr_prompts import build_ocr_prompt

logger = logging.getLogger(__name__)

WANDB_INFERENCE_BASE_URL = "https://api.inference.wandb.ai/v1"

# Vision-capable models on W&B Inference. Mapping is `model_id -> friendly label`
# and is sent verbatim to the frontend so the credentials modal can render the
# dropdown without hardcoding labels.
AVAILABLE_MODELS: dict[str, str] = {
    "moonshotai/Kimi-K2.5": "Kimi K2.5",
    "google/gemma-4-31B-it": "Gemma 4 31B",
    "Qwen/Qwen3.5-35B-A3B": "Qwen 3.5 35B A3B",
}
DEFAULT_MODEL = "moonshotai/Kimi-K2.5"


def resolve_model(requested: Optional[str]) -> str:
    """Return a valid model id, falling back to the default if missing/invalid."""
    if requested and requested in AVAILABLE_MODELS:
        return requested
    return DEFAULT_MODEL

# W&B Inference rejects very large base64-encoded image payloads ("ext_proc failed").
# Resize images so the longest edge is at most this many pixels before sending.
MAX_IMAGE_DIMENSION = 1600

# Gemma 4 emits a long reasoning trace before producing the final content. The
# OpenAI client surfaces only `message.content`, but reasoning still consumes
# token budget, so we set a generous ceiling here.
MAX_OUTPUT_TOKENS = 8192


def _ocr_inputs_for_trace(inputs: dict) -> dict:
    return {
        "image_base64": inputs.get("image_base64"),
        "contains_latex": inputs.get("contains_latex"),
        "contains_diagrams": inputs.get("contains_diagrams"),
        "custom_instructions": inputs.get("custom_instructions", ""),
    }


class OCROutput(BaseModel):
    """Structured output for OCR results."""
    markdown: str


# Manually-authored schema for json_schema strict mode (avoids `title` and other
# Pydantic-generated keys that strict-mode validators reject).
_OCR_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "OCROutput",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "markdown": {"type": "string"},
            },
            "required": ["markdown"],
            "additionalProperties": False,
        },
    },
}


class InferenceService:
    def __init__(
        self,
        api_key: str,
        entity: Optional[str] = None,
        project: Optional[str] = None,
        model: Optional[str] = None,
    ):
        kwargs = {
            "base_url": WANDB_INFERENCE_BASE_URL,
            "api_key": api_key,
            "timeout": 60.0,
        }
        if entity and project:
            kwargs["project"] = f"{entity}/{project}"
        self.client = AsyncOpenAI(**kwargs)
        self.model = resolve_model(model)

    @weave.op(postprocess_inputs=_ocr_inputs_for_trace)
    async def process_image(
        self,
        image_base64: str,
        mime_type: str,
        contains_latex: bool,
        contains_diagrams: bool,
        custom_instructions: str = "",
    ) -> str:
        """Process a single image with W&B Inference (gemma vision) using structured JSON output."""
        prompt = build_ocr_prompt(contains_latex, contains_diagrams, custom_instructions)

        t0 = time.perf_counter()
        send_b64, send_mime = self._maybe_downscale(image_base64, mime_type)
        t_resize = time.perf_counter() - t0
        in_kb = len(image_base64) * 3 / 4 / 1024
        out_kb = len(send_b64) * 3 / 4 / 1024
        logger.info(
            f"[inference] resize {t_resize*1000:.0f}ms ({in_kb:.0f}KB -> {out_kb:.0f}KB)"
        )

        t1 = time.perf_counter()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{send_mime};base64,{send_b64}",
                            },
                        },
                    ],
                }
            ],
            response_format=_OCR_RESPONSE_FORMAT,
            max_tokens=MAX_OUTPUT_TOKENS,
        )

        t_llm = time.perf_counter() - t1
        usage = getattr(response, "usage", None)
        prompt_toks = getattr(usage, "prompt_tokens", None) if usage else None
        completion_toks = getattr(usage, "completion_tokens", None) if usage else None
        logger.info(
            f"[inference] {self.model} call {t_llm:.2f}s "
            f"(prompt={prompt_toks} completion={completion_toks} "
            f"finish={response.choices[0].finish_reason})"
        )

        content = response.choices[0].message.content or ""
        try:
            parsed = OCROutput.model_validate_json(content)
            markdown = parsed.markdown
        except Exception:
            markdown = content

        result = self._clean_markdown(markdown)
        logger.info(
            f"[inference] total {time.perf_counter()-t0:.2f}s, output {len(result)} chars"
        )
        return result

    @staticmethod
    def _maybe_downscale(image_base64: str, mime_type: str) -> tuple[str, str]:
        """Decode, resize-if-needed, and re-encode as JPEG. Returns (base64, mime)."""
        raw = base64.b64decode(image_base64)
        try:
            img = Image.open(io.BytesIO(raw))
        except Exception:
            return image_base64, mime_type

        if max(img.size) <= MAX_IMAGE_DIMENSION:
            return image_base64, mime_type

        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Remove any markdown code fences that wrap the entire content."""
        text = re.sub(r'^```(?:markdown)?\s*\n?', '', text.strip())
        text = re.sub(r'\n?```\s*$', '', text.strip())
        return text.strip()
