from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = ["jpg", "jpeg", "png", "gif", "webp"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
