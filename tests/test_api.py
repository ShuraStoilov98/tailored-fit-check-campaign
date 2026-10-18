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
        data={"occasion": "Dinner", "campaign": "fit_test_a"},
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
