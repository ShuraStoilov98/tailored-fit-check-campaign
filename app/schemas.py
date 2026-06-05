from pydantic import BaseModel, Field


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
    overall_score: int = 4
    fit_score: int = 4
    style_score: int = 3
    colour_score: int = 4
    what_works: list[str]
    improvements: list[str]
    occasion_fit: str
    tailored_tip: str


class ErrorResponse(BaseModel):
    error: str


class PublicConfigResponse(BaseModel):
    app_store_cta_url: str
