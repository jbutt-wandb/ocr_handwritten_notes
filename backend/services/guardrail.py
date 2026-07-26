"""Prompt-injection guardrail for the custom-instructions field.

Wraps ``llm_guard``'s local ``PromptInjection`` scanner. No W&B / Weave
dependency — this is a plain process-wide singleton. The underlying model
downloads its weights on first construction, so we build it lazily and keep a
single instance per process.

Behavior mirrors the original design:
* Empty / whitespace-only instructions are skipped (``passed=True``).
* A scan that raises fails **open** (``passed=True``) so a scanner hiccup never
  blocks legitimate OCR.
* Otherwise ``passed`` reflects the scanner's validity verdict.
"""
from __future__ import annotations

import logging
from typing import Optional

from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.5


class Guardrail:
    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.threshold = threshold
        self._scanner = PromptInjection(
            threshold=threshold,
            match_type=MatchType.FULL,
        )

    def scan(self, custom_instructions: str) -> dict:
        if not custom_instructions or not custom_instructions.strip():
            return {"passed": True, "risk_score": 0.0, "skipped": True}
        try:
            _sanitized, is_valid, risk_score = self._scanner.scan(custom_instructions)
        except Exception as exc:  # noqa: BLE001 — fail open on scanner errors
            logger.warning("PromptInjection scanner failed, fail-open: %s", exc)
            return {"passed": True, "risk_score": 0.0, "fail_open": True, "error": str(exc)}
        return {"passed": bool(is_valid), "risk_score": float(risk_score)}


_guardrail_singleton: Optional[Guardrail] = None


def get_guardrail() -> Guardrail:
    """Return the process-wide ``Guardrail`` (built lazily on first use)."""
    global _guardrail_singleton
    if _guardrail_singleton is None:
        logger.info(
            "Loading Guardrail (first use, model download may take a moment)..."
        )
        _guardrail_singleton = Guardrail()
    return _guardrail_singleton
