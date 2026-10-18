import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app import APP_VERSION

logger = logging.getLogger(__name__)

# Keeps fire-and-forget tasks alive until they complete so the GC can't discard them.
_pending: set[asyncio.Task] = set()


def fire_and_forget(coro) -> None:
    """Schedule a coroutine as a background task without blocking the caller."""
    task = asyncio.create_task(coro)
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def log_event(
    webhook_url: str,
    event_type: str,
    *,
    campaign_id: str = "",
    source: str = "",
    slug: str = "",
    occasion: str = "",
    environment: str = "local",
    success: bool = True,
    error_message: str = "",
    verdict_label: str = "",
    overall_score: int | None = None,
    fit_score: int | None = None,
    style_score: int | None = None,
    colour_score: int | None = None,
) -> None:
    """POST a lightweight event payload to the Google Sheet webhook. No-ops if URL is blank."""
    if not webhook_url:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "campaign_id": campaign_id,
        "source": source,
        "slug": slug,
        "occasion": occasion,
        "environment": environment,
        "success": success,
        "error_message": error_message,
        "verdict_label": verdict_label,
        "overall_score": overall_score,
        "fit_score": fit_score,
        "style_score": style_score,
        "colour_score": colour_score,
        "app_version": APP_VERSION,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            await client.post(webhook_url, json=payload)
    except Exception as exc:
        logger.warning("Event logging failed (%s): %s", event_type, exc)


async def log_lead(
    webhook_url: str,
    *,
    email: str,
    marketing_consent: bool,
    campaign_id: str = "",
    source: str = "",
    slug: str = "",
    occasion: str = "",
    environment: str = "local",
    verdict_label: str = "",
    overall_score: int | None = None,
) -> None:
    """POST lead data to the Google Sheet webhook. Raises on failure so the caller can surface an error."""
    if not webhook_url:
        raise RuntimeError("Lead capture is not configured.")

    payload = {
        "type": "lead",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": email,
        "marketing_consent": marketing_consent,
        "campaign_id": campaign_id,
        "source": source,
        "slug": slug,
        "occasion": occasion,
        "environment": environment,
        "verdict_label": verdict_label,
        "overall_score": overall_score,
        "app_version": APP_VERSION,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Lead logging failed: %s", exc)
        raise
