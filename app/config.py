from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "local"
    max_upload_mb: int = 5
    app_store_cta_url: str = "https://go.tailored-to-you.com/try"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    google_sheet_webhook_url: str = ""
    rate_limit_window_seconds: int = 60
    fit_check_rate_limit: int = 8
    lead_rate_limit: int = 5
    allowed_image_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "image/heif-sequence",
        "application/octet-stream",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
