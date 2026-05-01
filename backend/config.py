from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OCR runtime settings
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = ["jpg", "jpeg", "png", "gif", "webp"]

    # Optional credentials sourced from .env (UI-managed file overrides these)
    openai_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"
        populate_by_name = True


settings = Settings()
