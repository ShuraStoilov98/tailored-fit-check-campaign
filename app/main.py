from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import APP_VERSION
from app.config import get_settings
from app.event_logging import fire_and_forget, log_event, log_lead
from app.fit_check import generate_fit_check
from app.image_processing import (
    ImageTooLargeError,
    UnsupportedImageFormatError,
    normalize_uploaded_image_bytes,
)
from app.rate_limit import RateLimiter
from app.security import RequestProtectionMiddleware
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
app = FastAPI(title="Tailored Fit Check Campaign", version=APP_VERSION)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

NO_OUTFIT_ERROR_CODE = "NO_OUTFIT_DETECTED"
NO_OUTFIT_ERROR_MESSAGE = "No outfit detected. Please try again with a clear outfit photo."
IMAGE_TOO_LARGE_ERROR_CODE = "IMAGE_TOO_LARGE"
UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE = "UNSUPPORTED_IMAGE_FORMAT"
RATE_LIMITED_ERROR_CODE = "RATE_LIMITED"

_fit_check_limiter = RateLimiter(
    max_requests=settings.fit_check_rate_limit,
    window_seconds=settings.rate_limit_window_seconds,
)
_lead_limiter = RateLimiter(
    max_requests=settings.lead_rate_limit,
    window_seconds=settings.rate_limit_window_seconds,
)
_event_limiter = RateLimiter(
    max_requests=settings.event_rate_limit,
    window_seconds=settings.rate_limit_window_seconds,
)
_api_global_limiter = RateLimiter(
    max_requests=settings.api_global_rate_limit,
    window_seconds=settings.rate_limit_window_seconds,
)
_fit_check_global_limiter = RateLimiter(
    max_requests=settings.fit_check_global_rate_limit,
    window_seconds=settings.rate_limit_window_seconds,
)
app.add_middleware(
    RequestProtectionMiddleware,
    max_upload_bytes=settings.max_upload_mb * 1024 * 1024,
    limiters={
        "/api/fit-check": _fit_check_limiter,
        "/api/lead": _lead_limiter,
        "/api/event": _event_limiter,
    },
    api_limiter=_api_global_limiter,
    fit_check_limiter=_fit_check_global_limiter,
    trust_railway_proxy=settings.trust_railway_proxy,
)


def _build_error_response(detail: str | dict) -> ErrorResponse:
    if isinstance(detail, dict):
        return ErrorResponse(
            error=str(detail.get("error") or "Something went wrong."),
            error_code=str(detail["error_code"]) if detail.get("error_code") else None,
        )
    return ErrorResponse(error=str(detail))


def _error_message_for_logging(detail: str | dict) -> str:
    if isinstance(detail, dict):
        return str(detail.get("error_code") or detail.get("error") or "error")
    return str(detail)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(exc.detail).model_dump(exclude_none=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error="Please check your input and try again.").model_dump(exclude_none=True),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Something went wrong while processing your request."
        ).model_dump(exclude_none=True),
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
    try:
        FitCheckRequestMeta(
            occasion=occasion,
            campaign_id=campaign_id,
            source=source,
            short_link_slug=slug,
        )
    except ValidationError:
        raise HTTPException(status_code=422, detail="Please check your input and try again.")

    if image.content_type and image.content_type not in settings.allowed_image_types:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE,
                "error": "This photo format is not supported. Please take a new photo or choose a JPEG/PNG image.",
            },
        )

    max_upload_bytes = settings.max_upload_mb * 1024 * 1024
    image_bytes = await image.read(max_upload_bytes + 1)
    if len(image_bytes) > max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail={"error_code": IMAGE_TOO_LARGE_ERROR_CODE, "error": "This photo is too large. Please choose a smaller image."},
        )
    try:
        image_bytes, image_content_type = normalize_uploaded_image_bytes(
            image_bytes,
            image.content_type or "",
            image.filename,
            max_upload_mb=settings.max_upload_mb,
        )
    except UnsupportedImageFormatError:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE,
                "error": "This photo format is not supported. Please take a new photo or choose a JPEG/PNG image.",
            },
        )
    except ImageTooLargeError:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": IMAGE_TOO_LARGE_ERROR_CODE,
                "error": "This photo is too large. Please try a screenshot or a smaller image.",
            },
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
        model_output = await generate_fit_check(
            image_bytes=image_bytes,
            content_type=image_content_type,
            occasion=occasion,
        )

        if not model_output.outfit_detected or model_output.fit_check is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": NO_OUTFIT_ERROR_CODE,
                    "error": NO_OUTFIT_ERROR_MESSAGE,
                },
            )
    except HTTPException as exc:
        fire_and_forget(
            log_event(
                settings.google_sheet_webhook_url,
                "error",
                success=False,
                error_message=_error_message_for_logging(exc.detail),
                **log_kwargs,
            )
        )
        raise

    fit_result = model_output.fit_check
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
            error_message=payload.error_message,
        )
    )
    return Response(status_code=204)
