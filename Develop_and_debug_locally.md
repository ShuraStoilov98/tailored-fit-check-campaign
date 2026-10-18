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
uvicorn app.main:app --reload
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

## Logs & errors

Uvicorn prints request logs and tracebacks to stdout. For API errors check the
response JSON — the `error_code` field is the fast signal:

| `error_code` | Meaning |
|---|---|
| `NO_OUTFIT_DETECTED` | Model saw no clear outfit |
| `UNSUPPORTED_IMAGE_FORMAT` | Bad content type/extension, or undecodable bytes |
| `IMAGE_TOO_LARGE` | Could not compress under `MAX_UPLOAD_MB` |
| `RATE_LIMITED` | Client exceeded the window budget |

Hitting `RATE_LIMITED` while testing? Restart the server — the limiter is in-memory.

## Useful checks

```bash
curl localhost:8000/health
curl -X POST localhost:8000/api/fit-check -F 'image=@path/to/photo.jpg'
node --check static/app.js && node --check static/result.js
```

## Deploy

Push to `main` — Railway builds from the `Dockerfile` and redeploys.
Environment variables live in the Railway dashboard, never in the repo.
