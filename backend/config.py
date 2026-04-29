from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OCR runtime settings
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = ["jpg", "jpeg", "png", "gif", "webp"]

    # Optional credentials sourced from .env (UI-managed file overrides these)
    wandb_api_key: Optional[str] = Field(default=None, alias="WANDB_API_KEY")
    weave_entity: Optional[str] = Field(default=None, alias="ENTITY")
    weave_project: Optional[str] = Field(default=None, alias="PROJECT")
    model: Optional[str] = Field(default=None, alias="MODEL")

    class Config:
        env_file = ".env"
        extra = "ignore"
        populate_by_name = True


settings = Settings()
