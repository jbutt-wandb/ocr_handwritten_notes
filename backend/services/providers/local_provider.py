import logging
import time

import httpx
from openai import NOT_GIVEN, APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from backend.prompts.ocr_prompts import build_ocr_prompt
from backend.services.providers.base import (
    OCRProvider,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnreachableError,
    clean_markdown,
)

logger = logging.getLogger(__name__)

# Local inference can be very slow (large vision models on CPU take minutes),
# but a dead server should fail fast — hence the short connect timeout and no retries.
REQUEST_TIMEOUT_SECONDS = 300

# Reasoning models (e.g. Gemma 4 via Ollama) emit their thinking as a separate
# `reasoning` field that consumes the completion budget but never reaches
# `message.content` — even a simple page can burn 6k+ tokens of reasoning before
# transcription starts, so give local models generous headroom. Ollama clamps
# this to what fits; vLLM rejects it with a 400 instead, which we detect and
# retry once without max_tokens (vLLM then defaults to the largest completion
# that fits its --max-model-len).
MAX_OUTPUT_TOKENS = 16384


def _is_budget_rejection(e: APIStatusError) -> bool:
    """True when the server rejected the request because max_tokens exceeds
    its context window (vLLM behavior; Ollama clamps instead)."""
    if e.status_code != 400:
        return False
    msg = (getattr(e, "message", None) or str(e)).lower()
    return "context length" in msg or "max_tokens" in msg or "max tokens" in msg


class LocalProvider(OCRProvider):
    """Any OpenAI-compatible local server: Ollama, LM Studio, vLLM, etc.

    Uses plain chat completions (no structured output / JSON mode — support is
    inconsistent across local servers) and relies on the prompt + clean_markdown.
    """

    name = "local"

    def __init__(self, base_url: str, model: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=api_key or "not-needed",  # SDK requires a non-empty key
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=5.0),
            max_retries=0,
        )

    async def process_image(
        self,
        image_base64: str,
        mime_type: str,
        contains_latex: bool,
        contains_diagrams: bool,
        custom_instructions: str = "",
    ) -> str:
        prompt = build_ocr_prompt(contains_latex, contains_diagrams, custom_instructions)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                        },
                    },
                ],
            }
        ]
        t0 = time.perf_counter()
        try:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model, messages=messages, max_tokens=MAX_OUTPUT_TOKENS
                )
            except APIStatusError as e:
                if not _is_budget_rejection(e):
                    raise
                logger.warning(
                    f"[local] {self.model} rejected max_tokens={MAX_OUTPUT_TOKENS} "
                    f"({getattr(e, 'message', None) or e}) — retrying without max_tokens"
                )
                response = await self.client.chat.completions.create(
                    model=self.model, messages=messages, max_tokens=NOT_GIVEN
                )
        except APITimeoutError as e:
            raise ProviderTimeoutError(
                f"Your local model server at {self.base_url} timed out after "
                f"{REQUEST_TIMEOUT_SECONDS}s. Local inference can be slow — try a smaller model."
            ) from e
        except APIConnectionError as e:
            raise ProviderUnreachableError(
                f"Could not reach your local model server at {self.base_url} — is it running?"
            ) from e
        except APIStatusError as e:
            if e.status_code == 404:
                raise ProviderError(
                    f"Model '{self.model}' was not found on your local server at "
                    f"{self.base_url}. Check the model name (e.g. `ollama pull {self.model}`).",
                    status_code=404,
                    code="local_model_not_found",
                ) from e
            msg = getattr(e, "message", None) or str(e)
            raise ProviderError(msg, status_code=e.status_code, code="local_error") from e

        choice = response.choices[0]
        markdown = choice.message.content or ""
        usage = response.usage
        # Reasoning models return their thinking out-of-band (message.reasoning);
        # surfaced here because it explains empty/truncated content.
        reasoning = (choice.message.model_extra or {}).get("reasoning") or ""
        logger.info(
            f"[local] {self.model} call {time.perf_counter() - t0:.2f}s "
            f"(prompt={getattr(usage, 'prompt_tokens', None)} "
            f"completion={getattr(usage, 'completion_tokens', None)} "
            f"finish={choice.finish_reason} "
            f"content_chars={len(markdown)} reasoning_chars={len(reasoning)})"
        )

        budget = getattr(usage, "completion_tokens", None) or MAX_OUTPUT_TOKENS
        if not markdown.strip():
            if choice.finish_reason == "length":
                raise ProviderError(
                    f"Model '{self.model}' used its entire {budget}-token output "
                    "budget on internal reasoning before producing any text. Try a less "
                    "verbose model, or a simpler/smaller page.",
                    status_code=502,
                    code="local_output_truncated",
                )
            raise ProviderError(
                f"Model '{self.model}' returned an empty response. It may not support "
                "image input — use a vision-capable model.",
                status_code=502,
                code="local_error",
            )
        if choice.finish_reason == "length":
            logger.warning(
                f"[local] {self.model} output truncated at {budget} tokens — "
                "transcription may be incomplete"
            )
        return clean_markdown(markdown)
