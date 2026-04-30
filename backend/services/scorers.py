from __future__ import annotations

import logging
from typing import Any, Optional

import weave
from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType

logger = logging.getLogger(__name__)


class PromptInjectionScorer(weave.Scorer):
    threshold: float = 0.5

    def model_post_init(self, __context: Any) -> None:
        self._scanner = PromptInjection(
            threshold=self.threshold,
            match_type=MatchType.FULL,
        )

    @weave.op
    def score(self, output: str) -> dict:
        if not output or not output.strip():
            return {"passed": True, "risk_score": 0.0, "skipped": True}
        try:
            _sanitized, is_valid, risk_score = self._scanner.scan(output)
        except Exception as exc:
            logger.warning("PromptInjection scanner failed, fail-open: %s", exc)
            return {
                "passed": True,
                "risk_score": 0.0,
                "fail_open": True,
                "error": str(exc),
            }
        return {"passed": bool(is_valid), "risk_score": float(risk_score)}


_scorer: Optional[PromptInjectionScorer] = None


def get_injection_scorer() -> PromptInjectionScorer:
    global _scorer
    if _scorer is None:
        logger.info("Loading PromptInjectionScorer (first use, model download may take a moment)...")
        _scorer = PromptInjectionScorer()
        try:
            weave.publish(_scorer, name="prompt-injection-scorer")
        except Exception as exc:
            logger.warning("weave.publish failed for scorer: %s", exc)
    return _scorer
