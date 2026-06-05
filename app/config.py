from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "local"
    max_upload_mb: int = 5
    app_store_cta_url: str = "https://go.tailored-to-you.com/try"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    google_sheet_webhook_url: str = ""
    allowed_image_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
