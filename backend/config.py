from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OCR runtime settings
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = ["jpg", "jpeg", "png", "gif", "webp"]

    # Optional credentials sourced from .env (UI-managed file overrides these)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None

    # Local OpenAI-compatible server (Ollama, LM Studio, vLLM). No default URL here —
    # that would make "local" look configured on every install; the UI supplies it.
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None
    local_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"
        populate_by_name = True


settings = Settings()
