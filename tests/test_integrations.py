"""Provider errors stay friendly and do not copy private payloads into logs."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app import event_logging, fit_check


@pytest.mark.parametrize("raw", ["not JSON: private@example.com", "[]", '{"outfit_detected": true}'])
def test_invalid_ai_output_is_handled_without_logging_content(monkeypatch, caplog, raw):
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))])
    create = AsyncMock(return_value=completion)
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(fit_check, "get_settings", lambda: SimpleNamespace(openai_api_key="test", openai_model="mock"))
    monkeypatch.setattr(fit_check, "_get_client", lambda key: fake_client)

    with pytest.raises(HTTPException) as error:
        asyncio.run(fit_check.generate_fit_check(image_bytes=b"private image", content_type="image/jpeg", occasion=None))
    assert error.value.status_code == 502
    assert raw not in caplog.text
    assert "private image" not in caplog.text
    assert "private@example.com" not in caplog.text


def test_ai_timeout_is_friendly_and_does_not_log_exception_text(monkeypatch, caplog):
    create = AsyncMock(side_effect=TimeoutError("private request payload"))
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(fit_check, "get_settings", lambda: SimpleNamespace(openai_api_key="test", openai_model="mock"))
    monkeypatch.setattr(fit_check, "_get_client", lambda key: fake_client)
    with pytest.raises(HTTPException) as error:
        asyncio.run(fit_check.generate_fit_check(image_bytes=b"image", content_type="image/jpeg", occasion=None))
    assert error.value.status_code == 502
    assert "private request payload" not in caplog.text


def test_failed_lead_webhook_does_not_log_its_url_or_email(monkeypatch, caplog):
    webhook = "https://example.com/private-webhook-token"
    response = httpx.Response(500, request=httpx.Request("POST", webhook))
    context = AsyncMock()
    context.__aenter__.return_value.post.return_value = response
    monkeypatch.setattr(event_logging.httpx, "AsyncClient", lambda **kwargs: context)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(event_logging.log_lead(webhook, email="private@example.com", marketing_consent=True))
    assert "private-webhook-token" not in caplog.text
    assert "private@example.com" not in caplog.text
