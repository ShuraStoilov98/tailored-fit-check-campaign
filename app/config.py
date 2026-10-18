from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "local"
    max_upload_mb: int = Field(default=5, ge=1, le=20)
    app_store_cta_url: str = "https://go.tailored-to-you.com/try"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    google_sheet_webhook_url: str = ""
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    fit_check_rate_limit: int = Field(default=8, ge=1)
    lead_rate_limit: int = Field(default=5, ge=1)
    event_rate_limit: int = Field(default=60, ge=1)
    api_global_rate_limit: int = Field(default=240, ge=1)
    fit_check_global_rate_limit: int = Field(default=40, ge=1)
    trust_railway_proxy: bool = False
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
