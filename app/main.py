from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.event_logging import fire_and_forget, log_event, log_lead
from app.fit_check import generate_fit_check
from app.schemas import (
    ErrorResponse,
    EventLogRequest,
    FitCheckRequestMeta,
    FitCheckResponse,
    HealthResponse,
    LeadRequest,
    PublicConfigResponse,
)

settings = get_settings()
app = FastAPI(title="Tailored Fit Check Campaign", version="2.0.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Something went wrong."
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=detail).model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error="Please check your input and try again.").model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Something went wrong while processing your request.").model_dump(),
    )


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get("/result", include_in_schema=False)
async def result_page() -> FileResponse:
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
    FitCheckRequestMeta(
        occasion=occasion,
        campaign_id=campaign_id,
        source=source,
        short_link_slug=slug,
    )

    if image.content_type not in settings.allowed_image_types:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG, or WEBP image.")

    image_bytes = await image.read()
    if len(image_bytes) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Image is too large. Max size is {settings.max_upload_mb} MB.",
        )

    log_kwargs = dict(
        campaign_id=campaign_id or "",
        source=source or "",
        slug=slug or "",
        occasion=occasion or "",
        environment=settings.environment,
    )
    fire_and_forget(log_event(settings.google_sheet_webhook_url, "fit_check_started", **log_kwargs))

    try:
        fit_result = await generate_fit_check(
            image_bytes=image_bytes,
            content_type=image.content_type or "",
            occasion=occasion,
        )
    except HTTPException as exc:
        fire_and_forget(
            log_event(
                settings.google_sheet_webhook_url,
                "error",
                success=False,
                error_message=str(exc.detail),
                **log_kwargs,
            )
        )
        raise

    fire_and_forget(
        log_event(
            settings.google_sheet_webhook_url,
            "fit_check_completed",
            verdict_label=fit_result.verdict_label,
            overall_score=fit_result.overall_score,
            fit_score=fit_result.fit_score,
            style_score=fit_result.style_score,
            colour_score=fit_result.colour_score,
            **log_kwargs,
        )
    )
    return fit_result


@app.post("/api/lead")
async def capture_lead(payload: LeadRequest) -> JSONResponse:
    if not payload.marketing_consent:
        raise HTTPException(status_code=400, detail="Marketing consent is required.")

    try:
        await log_lead(
            settings.google_sheet_webhook_url,
            email=str(payload.email),
            marketing_consent=payload.marketing_consent,
            campaign_id=payload.campaign_id,
            source=payload.source,
            slug=payload.slug,
            occasion=payload.occasion,
            environment=settings.environment,
            verdict_label=payload.verdict_label,
            overall_score=payload.overall_score,
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="We couldn't save your email just now. Please try again.",
        )

    fire_and_forget(
        log_event(
            settings.google_sheet_webhook_url,
            "email_submitted",
            campaign_id=payload.campaign_id,
            source=payload.source,
            slug=payload.slug,
            occasion=payload.occasion,
            environment=settings.environment,
            verdict_label=payload.verdict_label,
            overall_score=payload.overall_score,
        )
    )
    return JSONResponse({"ok": True})


@app.post("/api/event")
async def track_event(payload: EventLogRequest) -> Response:
    fire_and_forget(
        log_event(
            settings.google_sheet_webhook_url,
            payload.event_type,
            campaign_id=payload.campaign_id,
            source=payload.source,
            slug=payload.slug,
            occasion=payload.occasion,
            environment=settings.environment,
        )
    )
    return Response(status_code=204)
