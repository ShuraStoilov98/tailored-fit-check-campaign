# Develop & Debug Locally

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # includes runtime deps + pytest
cp .env.example .env
```

You can leave `OPENAI_API_KEY` blank: with `ENVIRONMENT=local` and no key, the app
returns a canned Fit Check so you can work on the frontend without spending credit.

## Run

```bash
uvicorn app.main:app --reload --no-proxy-headers --no-access-log
```

App is at `http://localhost:8000`.

To exercise campaign tracking, open:

```text
http://localhost:8000/?campaign=fit_test_a&source=qr&slug=fit-test-a
```

## Test

```bash
pytest -q
```

The suite is offline by design — `tests/conftest.py` blanks `OPENAI_API_KEY` and the
webhook URL before the app is imported, so nothing hits the network.

## Key env vars (`.env`)

| Var | Required | Notes |
|-----|----------|-------|
| `OPENAI_API_KEY` | Prod only | Blank locally → mock Fit Check |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `APP_STORE_CTA_URL` | No | Served to the frontend via `/api/public-config` |
| `GOOGLE_SHEET_WEBHOOK_URL` | No | Blank → event logging is skipped |
| `MAX_UPLOAD_MB` | No | Default: `5` |
| `ENVIRONMENT` | No | Set to `local` for dev |
| `FIT_CHECK_RATE_LIMIT` | No | Default: `8` per 60s per client |
| `LEAD_RATE_LIMIT` | No | Default: `5` per 60s per client |
| `EVENT_RATE_LIMIT` | No | Default: `60` per 60s per client |
| `API_GLOBAL_RATE_LIMIT` | No | Default: `240` API POSTs per 60s per process |
| `FIT_CHECK_GLOBAL_RATE_LIMIT` | No | Default: `40` Fit Checks per 60s per process |
| `TRUST_RAILWAY_PROXY` | No | Leave `false` locally; Railway-only opt-in described in README |

## Logs & errors

The documented command disables Uvicorn access logs to keep IPs and URL parameters
out of them. Application warnings report error types without upstream response text.
For API errors check the
response JSON — the `error_code` field is the fast signal:

| `error_code` | Meaning |
|---|---|
| `NO_OUTFIT_DETECTED` | Model saw no clear outfit |
| `UNSUPPORTED_IMAGE_FORMAT` | Bad content type/extension, or undecodable bytes |
| `IMAGE_TOO_LARGE` | File exceeds `MAX_UPLOAD_MB` or decoded image exceeds 20 megapixels |
| `REQUEST_TOO_LARGE` | JSON request exceeds 16 KB |
| `RATE_LIMITED` | Client exceeded the window budget |

Hitting `RATE_LIMITED` while testing? Restart the server — the limiter is in-memory.

## Useful checks

```bash
curl localhost:8000/health
curl -X POST localhost:8000/api/fit-check -F 'image=@path/to/photo.jpg'
node --check static/app.js && node --check static/result.js
python scripts/check_secrets.py
```

## Deploy

Push to `main` — Railway builds from the `Dockerfile` and redeploys.
Environment variables live in the Railway dashboard, never in the repo.
Use one worker/replica for the in-memory rate limits. Set `ENVIRONMENT=production`;
enable `TRUST_RAILWAY_PROXY=true` only for ingress-only Railway deployments.
