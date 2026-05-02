import re
from abc import ABC, abstractmethod

from pydantic import BaseModel


class OCROutput(BaseModel):
    """Structured output schema shared across providers."""
    markdown: str


class ProviderError(Exception):
    """Provider-agnostic error with HTTP status hint and stable code."""

    def __init__(self, message: str, *, status_code: int = 502, code: str = "provider_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ProviderTimeoutError(ProviderError):
    def __init__(self, message: str):
        super().__init__(message, status_code=504, code="provider_timeout")


class ProviderUnreachableError(ProviderError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502, code="provider_unreachable")


def clean_markdown(text: str) -> str:
    """Strip enclosing ```markdown fences a model occasionally adds."""
    text = re.sub(r"^```(?:markdown)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```\s*$", "", text.strip())
    return text.strip()


class OCRProvider(ABC):
    name: str

    @abstractmethod
    async def process_image(
        self,
        image_base64: str,
        mime_type: str,
        contains_latex: bool,
        contains_diagrams: bool,
        custom_instructions: str = "",
    ) -> str:
        ...
