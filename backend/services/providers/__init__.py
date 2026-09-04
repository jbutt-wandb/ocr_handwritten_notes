from typing import Optional

from backend.services.credentials import CredentialStore
from backend.services.providers.anthropic_provider import AnthropicProvider
from backend.services.providers.base import (
    OCROutput,
    OCRProvider,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnreachableError,
)
from backend.services.providers.gemini_provider import GeminiProvider
from backend.services.providers.local_provider import LocalProvider
from backend.services.providers.mistral_provider import MistralProvider
from backend.services.providers.openai_provider import OpenAIProvider

SUPPORTED_PROVIDERS = ("openai", "anthropic", "gemini", "mistral", "local")


class ProviderNotConfigured(Exception):
    def __init__(self, provider: str):
        super().__init__(f"Provider '{provider}' is not configured")
        self.provider = provider


def get_provider(name: str, store: CredentialStore) -> OCRProvider:
    """Build a provider instance from the credential store. Raises ProviderNotConfigured
    if the corresponding credentials are missing."""
    if name not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {name}")

    if name == "local":
        base_url = store.get_field("local_base_url")
        model = store.get_field("local_model")
        if not (base_url and model):
            raise ProviderNotConfigured("local")
        return LocalProvider(
            base_url=base_url, model=model, api_key=store.get_field("local_api_key")
        )

    key: Optional[str] = store.get_key(name)
    if not key:
        raise ProviderNotConfigured(name)

    if name == "openai":
        return OpenAIProvider(key)
    if name == "anthropic":
        return AnthropicProvider(key)
    if name == "gemini":
        return GeminiProvider(key)
    if name == "mistral":
        return MistralProvider(key)
    raise ValueError(f"Unsupported provider: {name}")  # unreachable


__all__ = [
    "SUPPORTED_PROVIDERS",
    "OCRProvider",
    "OCROutput",
    "ProviderError",
    "ProviderTimeoutError",
    "ProviderUnreachableError",
    "ProviderNotConfigured",
    "get_provider",
]
