"""End-to-end checks for the public API surface."""


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_landing_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_result_page_loads(client):
    assert client.get("/result").status_code == 200


def test_public_config_exposes_only_the_cta_url(client):
    response = client.get("/api/public-config")
    assert response.status_code == 200
    # Guards the non-negotiable: no secret may reach the frontend.
    assert set(response.json()) == {"app_store_cta_url"}


def test_fit_check_returns_structured_verdict(client, jpeg_bytes):
    response = client.post(
        "/api/fit-check",
        files={"image": ("outfit.jpg", jpeg_bytes, "image/jpeg")},
        data={"occasion": "Dinner", "campaign_id": "fit_test_a"},
    )
    assert response.status_code == 200

    body = response.json()
    assert set(body) >= {
        "verdict_label",
        "one_line_verdict",
        "what_works",
        "improvements",
        "occasion_fit",
        "tailored_tip",
    }
    assert len(body["what_works"]) == 2
    assert len(body["improvements"]) == 3
    for field in ("overall_score", "fit_score", "style_score", "colour_score"):
        assert 1 <= body[field] <= 5


def test_fit_check_rejects_unsupported_format(client):
    response = client.post(
        "/api/fit-check",
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_IMAGE_FORMAT"


def test_fit_check_rejects_corrupt_image(client):
    response = client.post(
        "/api/fit-check",
        files={"image": ("outfit.jpg", b"\xff\xd8not-really-a-jpeg", "image/jpeg")},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_IMAGE_FORMAT"


def test_fit_check_is_rate_limited(client, jpeg_bytes):
    files = {"image": ("outfit.jpg", jpeg_bytes, "image/jpeg")}
    for _ in range(5):
        assert client.post("/api/fit-check", files=files).status_code == 200

    blocked = client.post("/api/fit-check", files=files)
    assert blocked.status_code == 429
    assert blocked.json()["error_code"] == "RATE_LIMITED"


def test_lead_requires_marketing_consent(client):
    response = client.post(
        "/api/lead",
        json={"email": "someone@example.com", "marketing_consent": False},
    )
    assert response.status_code == 400


def test_lead_rejects_invalid_email(client):
    response = client.post(
        "/api/lead",
        json={"email": "not-an-email", "marketing_consent": True},
    )
    assert response.status_code == 422


def test_lead_degrades_gracefully_when_webhook_unconfigured(client):
    response = client.post(
        "/api/lead",
        json={"email": "someone@example.com", "marketing_consent": True},
    )
    assert response.status_code == 502
    assert "error" in response.json()


def test_event_logging_accepts_campaign_context(client):
    response = client.post(
        "/api/event",
        json={
            "event_type": "page_view",
            "campaign_id": "fit_conf_london_a",
            "source": "qr",
            "slug": "fit-conf-london-a",
        },
    )
    assert response.status_code == 204


def test_errors_never_leak_internals(client):
    response = client.post("/api/event", json={"event_type": "x" * 500})
    assert response.status_code == 422
    assert response.json() == {"error": "Please check your input and try again."}


def test_fit_check_rejects_large_body_before_decoding(client, jpeg_bytes, monkeypatch):
    def unexpected_decode(*args, **kwargs):
        raise AssertionError("Oversized uploads must not reach the image decoder")

    monkeypatch.setattr("app.main.normalize_uploaded_image_bytes", unexpected_decode)
    response = client.post(
        "/api/fit-check",
        files={"image": ("outfit.jpg", jpeg_bytes + b"\x00" * (6 * 1024 * 1024), "image/jpeg")},
    )
    assert response.status_code == 413
    assert response.json()["error_code"] == "IMAGE_TOO_LARGE"


def test_file_limit_is_enforced_within_multipart_overhead_allowance(client, jpeg_bytes):
    # Body overhead allowance must not increase the actual file-size limit.
    photo = jpeg_bytes + b"\x00" * (5 * 1024 * 1024 + 1 - len(jpeg_bytes))
    response = client.post("/api/fit-check", files={"image": ("outfit.jpg", photo, "image/jpeg")})
    assert response.status_code == 413
    assert response.json()["error_code"] == "IMAGE_TOO_LARGE"


def test_file_at_upload_limit_is_accepted(client, jpeg_bytes):
    photo = jpeg_bytes + b"\x00" * (5 * 1024 * 1024 - len(jpeg_bytes))
    response = client.post("/api/fit-check", files={"image": ("outfit.jpg", photo, "image/jpeg")})
    assert response.status_code == 200


def test_forwarded_headers_do_not_reset_the_fit_check_budget(client, jpeg_bytes):
    statuses = []
    for index in range(6):
        response = client.post(
            "/api/fit-check",
            files={"image": ("outfit.jpg", jpeg_bytes, "image/jpeg")},
            headers={"X-Forwarded-For": f"198.51.100.{index}", "X-Real-IP": f"192.0.2.{index}"},
        )
        statuses.append(response.status_code)
    assert statuses == [200] * 5 + [429]
    assert response.headers["retry-after"] == "60"


def test_overlong_form_metadata_returns_friendly_validation_error(client, jpeg_bytes):
    response = client.post(
        "/api/fit-check", files={"image": ("outfit.jpg", jpeg_bytes, "image/jpeg")},
        data={"occasion": "x" * 81},
    )
    assert response.status_code == 422
    assert response.json() == {"error": "Please check your input and try again."}


def test_events_are_limited_before_logging(client, monkeypatch):
    from app import main

    calls = []

    async def record(*args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(main, "log_event", record)
    for _ in range(10):
        assert client.post("/api/event", json={"event_type": "page_view"}).status_code == 204
    assert client.post("/api/event", json={"event_type": "page_view"}).status_code == 429
    assert len(calls) == 10


def test_events_reject_unknown_or_server_only_names(client):
    for name in ("arbitrary_event", "fit_check_completed", "email_submitted"):
        assert client.post("/api/event", json={"event_type": name}).status_code == 422


def test_events_reject_free_text_error_messages(client):
    response = client.post("/api/event", json={"event_type": "error", "error_message": "someone@example.com"})
    assert response.status_code == 422
    assert "someone@example.com" not in response.text
    assert client.post("/api/event", json={"event_type": "error", "error_message": "IMAGE_TOO_LARGE"}).status_code == 204


def test_json_body_limit_applies_to_events_and_leads(client):
    for path in ("/api/event", "/api/lead"):
        response = client.post(path, content=b"x" * (17 * 1024), headers={"Content-Type": "application/json"})
        assert response.status_code == 413
        assert response.json()["error_code"] == "REQUEST_TOO_LARGE"


def test_lead_is_rate_limited_even_when_json_is_invalid(client):
    for _ in range(5):
        assert client.post("/api/lead", json={}).status_code == 422
    assert client.post("/api/lead", json={}).status_code == 429


def test_successful_lead_capture_preserves_consent_and_campaign(client, monkeypatch):
    from app import main

    captured = []

    async def record(webhook, **payload):
        captured.append(payload)

    monkeypatch.setattr(main, "log_lead", record)
    response = client.post("/api/lead", json={
        "email": "someone@example.com", "marketing_consent": True,
        "campaign_id": "test_campaign", "source": "qr", "slug": "test-slug",
    })
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured[0]["marketing_consent"] is True
    assert captured[0]["campaign_id"] == "test_campaign"
    assert captured[0]["source"] == "qr"
    assert captured[0]["slug"] == "test-slug"


def test_privacy_notice_is_available_on_both_pages(client):
    for path in ("/", "/result"):
        response = client.get(path)
        assert 'id="privacy-notice"' in response.text
        assert "OpenAI" in response.text
        assert 'href="#privacy-notice"' in response.text
