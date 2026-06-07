# Develop & Debug Locally

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY at minimum
```

## Run

```bash
uvicorn app.main:app --reload
```

App is at `http://localhost:8000`

## Key env vars (`.env`)

| Var | Required | Notes |
|-----|----------|-------|
| `OPENAI_API_KEY` | Yes | Powers the fit check |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `GOOGLE_SHEET_WEBHOOK_URL` | No | Lead capture; skipped if blank |
| `MAX_UPLOAD_MB` | No | Default: `5` |
| `ENVIRONMENT` | No | Set to `local` for dev |

## Logs & errors

Uvicorn prints request logs and tracebacks to stdout. For API errors check the response JSON — the `error_code` field is the fast signal.

## Deploy

Push to `main` — Railway picks it up automatically and redeploys.
