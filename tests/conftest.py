"""Test configuration.

Environment variables are set before `app` is imported so that pydantic-settings
reads them instead of any real local `.env`. This keeps the suite offline: no
OpenAI key means the Fit Check falls back to its built-in mock, and a blank
webhook URL makes event logging a no-op.
"""

import os

os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_SHEET_WEBHOOK_URL"] = ""
os.environ["ENVIRONMENT"] = "local"
os.environ["FIT_CHECK_RATE_LIMIT"] = "5"
os.environ["LEAD_RATE_LIMIT"] = "5"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["EVENT_RATE_LIMIT"] = "10"
os.environ["API_GLOBAL_RATE_LIMIT"] = "240"
os.environ["FIT_CHECK_GLOBAL_RATE_LIMIT"] = "40"
os.environ["TRUST_RAILWAY_PROXY"] = "false"
os.environ["MAX_UPLOAD_MB"] = "5"

from io import BytesIO  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import main  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Each test starts with a clean rate-limit budget."""
    main._fit_check_limiter._hits.clear()
    main._lead_limiter._hits.clear()
    main._event_limiter._hits.clear()
    main._api_global_limiter._hits.clear()
    main._fit_check_global_limiter._hits.clear()
    yield


@pytest.fixture
def jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (120, 160), color=(90, 90, 120)).save(buffer, format="JPEG")
    return buffer.getvalue()
