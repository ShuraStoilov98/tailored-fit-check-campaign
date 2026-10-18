from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

ScoreInt = Annotated[int, Field(ge=1, le=5)]


class HealthResponse(BaseModel):
    ok: bool = True


class FitCheckRequestMeta(BaseModel):
    occasion: str | None = Field(default=None, max_length=80)
    campaign_id: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=80)
    short_link_slug: str | None = Field(default=None, max_length=120)


class FitCheckResponse(BaseModel):
    verdict_label: str
    one_line_verdict: str
    overall_score: ScoreInt = 4
    fit_score: ScoreInt = 4
    style_score: ScoreInt = 3
    colour_score: ScoreInt = 4
    what_works: list[str]
    improvements: list[str]
    occasion_fit: str
    tailored_tip: str


class FitCheckModelOutput(BaseModel):
    outfit_detected: bool
    no_outfit_message: str = "No outfit detected. Please try again with a clear outfit photo."
    fit_check: FitCheckResponse | None = None

    @model_validator(mode="after")
    def validate_fit_check_payload(self) -> "FitCheckModelOutput":
        if self.outfit_detected and self.fit_check is None:
            raise ValueError("fit_check is required when outfit_detected is true")
        if not self.outfit_detected:
            self.fit_check = None
        return self


class EventLogRequest(BaseModel):
    # Completion and email events are emitted by the server after success.
    event_type: Literal[
        "page_view", "photo_selected", "app_cta_clicked",
        "google_play_cta_clicked", "logo_clicked", "error",
    ]
    campaign_id: str = Field(default="", max_length=120)
    source: str = Field(default="", max_length=80)
    slug: str = Field(default="", max_length=120)
    occasion: str = Field(default="", max_length=80)
    error_message: Literal[
        "", "NO_OUTFIT_DETECTED", "IMAGE_TOO_LARGE", "UNSUPPORTED_IMAGE_FORMAT",
        "IMAGE_NORMALIZATION_FAILED", "RATE_LIMITED", "FIT_CHECK_FAILED",
    ] = ""


class LeadRequest(BaseModel):
    email: EmailStr
    marketing_consent: bool
    campaign_id: str = Field(default="", max_length=120)
    source: str = Field(default="", max_length=80)
    slug: str = Field(default="", max_length=120)
    occasion: str = Field(default="", max_length=80)
    verdict_label: str = Field(default="", max_length=120)
    overall_score: ScoreInt | None = None


class ErrorResponse(BaseModel):
    error: str
    error_code: str | None = None


class PublicConfigResponse(BaseModel):
    app_store_cta_url: str
