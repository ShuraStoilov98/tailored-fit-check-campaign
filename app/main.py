from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.schemas import (
    ErrorResponse,
    FitCheckRequestMeta,
    FitCheckResponse,
    HealthResponse,
    PublicConfigResponse,
)


settings = get_settings()
app = FastAPI(title="Tailored Fit Check Campaign", version="0.1.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Something went wrong."
    payload = ErrorResponse(error=detail)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    payload = ErrorResponse(error="Please check your input and try again.")
    return JSONResponse(status_code=422, content=payload.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, __: Exception) -> JSONResponse:
    payload = ErrorResponse(error="Something went wrong while processing your request.")
    return JSONResponse(status_code=500, content=payload.model_dump())


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get("/result", include_in_schema=False)
async def result() -> FileResponse:
    return FileResponse(STATIC_DIR / "result.html")


@app.get("/api/public-config", response_model=PublicConfigResponse)
async def public_config() -> PublicConfigResponse:
    return PublicConfigResponse(app_store_cta_url=settings.app_store_cta_url)


@app.post("/api/fit-check", response_model=FitCheckResponse)
async def fit_check(
    image: UploadFile = File(...),
    occasion: str | None = Form(default=None),
    campaign_id: str | None = Form(default=None),
    source: str | None = Form(default=None),
    slug: str | None = Form(default=None),
) -> FitCheckResponse:
    _meta = FitCheckRequestMeta(
        occasion=occasion,
        campaign_id=campaign_id,
        source=source,
        short_link_slug=slug,
    )

    if image.content_type not in settings.allowed_image_types:
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPG, PNG, or WEBP image.",
        )

    # Read request bytes in memory only; we do not persist photos to disk.
    image_bytes = await image.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image is too large. Max size is {settings.max_upload_mb} MB.",
        )

    occasion_text = occasion.strip() if occasion else "everyday"

    return FitCheckResponse(
        verdict_label="Strong base",
        one_line_verdict="Clean foundation with one easy tweak.",
        overall_score=4,
        fit_score=4,
        style_score=3,
        colour_score=4,
        what_works=[
            "Balanced base",
            "Palette feels cohesive",
        ],
        improvements=[
            "Add one sharper finishing touch",
            "Choose cleaner shoe lines",
            "Use one subtle accessory",
        ],
        occasion_fit=f"Works well for {occasion_text}.",
        tailored_tip="Small styling changes can make the outfit feel more intentional.",
    )
