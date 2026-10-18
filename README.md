# Tailored Fit Check Campaign

[![CI](https://github.com/ShuraStoilov98/tailored-fit-check-campaign/actions/workflows/ci.yml/badge.svg)](https://github.com/ShuraStoilov98/tailored-fit-check-campaign/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

A lightweight, no-login web app for Tailored's **Daily Fit Check** growth experiments.

Someone scans a QR code on a London street or at a conference, takes a photo of their outfit, and gets a short AI styling verdict in about 30 seconds — then sees an app download CTA and an email capture. Every step is tracked so we can tell which channels, locations, and hooks actually drive engagement.

This is deliberately **separate** from the main Tailored app: no Firebase Auth, no user profiles, no production database, and no photo storage.

---

## Screens

| Landing | Result |
|---|---|
| <img src="docs/images/landing.png" alt="Mobile landing page with photo upload, occasion chips, and Get My Fit Check CTA" width="320"> | <img src="docs/images/result.png" alt="Result page with overall score, fit/style/colour sub-scores, what works, improvements, and app CTA" width="320"> |

*The outfit photo in the result screenshot is a neutral placeholder — real uploads are never stored.*

---

## How it works

```mermaid
flowchart TD
    A["📱 QR code<br/>(Short.io branded link)"] --> B["Landing page<br/>campaign / source / slug<br/>read from URL params"]
    B --> C["Take or upload<br/>outfit photo"]
    C --> D["Optional:<br/>pick an occasion"]
    D --> E["POST /api/fit-check"]
    E --> F["Resize + re-encode<br/>in memory"]
    F --> G["OpenAI vision call<br/>(backend only)"]
    G --> H{"Outfit<br/>detected?"}
    H -- No --> I["Friendly retry prompt"]
    H -- Yes --> J["Result card<br/>scores + styling notes"]
    J --> K["App Store / Google Play CTA"]
    J --> L["Email capture<br/>+ marketing consent"]
    K --> M["Events → Google Sheet"]
    L --> M
```

## Architecture

A single FastAPI service that serves its own static frontend. One process, one deploy, no build step.

```mermaid
flowchart LR
    subgraph Browser["📱 Mobile browser"]
        UI["static/<br/>index.html · app.js<br/>result.html · result.js"]
    end

    subgraph Service["FastAPI service (Railway)"]
        R["main.py<br/>routes + error handling"]
        RL["rate_limit.py<br/>per-IP throttle"]
        IP["image_processing.py<br/>resize · re-encode · validate"]
        FC["fit_check.py<br/>+ prompts.py"]
        EL["event_logging.py<br/>fire-and-forget"]
    end

    OA["OpenAI<br/>vision model"]
    GS["Google Sheet<br/>webhook"]

    UI -->|"multipart photo"| R
    R --> RL
    R --> IP
    IP -->|"JPEG bytes"| FC
    FC -->|"API key stays<br/>server-side"| OA
    OA -->|"structured JSON"| FC
    R -.->|"async, never blocks"| EL
    EL --> GS

    style OA fill:#D0B98C,stroke:#8a7a52,color:#1a1a1a
    style GS fill:#D0B98C,stroke:#8a7a52,color:#1a1a1a
```

**Why this shape:** the photo is held in memory, resized, re-encoded to JPEG, sent to OpenAI, and dropped. It never touches disk and never reaches a database. Analytics calls are fire-and-forget so a slow webhook can never delay a user's verdict.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # add your OPENAI_API_KEY
uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

Without an `OPENAI_API_KEY`, the app runs in **mock mode** locally and returns a canned verdict — handy for frontend work and for the test suite.

### Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite is fully offline: no API key, no network, no spend.

---

## API

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/result` | Result page |
| `GET` | `/health` | Liveness probe → `{"ok": true}` |
| `GET` | `/api/public-config` | App CTA URL (the only config the frontend sees) |
| `POST` | `/api/fit-check` | Photo in, structured verdict out |
| `POST` | `/api/lead` | Email capture, requires `marketing_consent` |
| `POST` | `/api/event` | Lightweight campaign event |

`POST /api/fit-check` takes a multipart `image` plus optional `occasion`, `campaign_id`, `source`, and `slug`, and returns:

```json
{
  "verdict_label": "Strong base",
  "one_line_verdict": "Clean tailoring with one sharper finishing touch to go.",
  "overall_score": 4,
  "fit_score": 4,
  "style_score": 4,
  "colour_score": 5,
  "what_works": ["Balanced proportions throughout", "Palette feels cohesive"],
  "improvements": [
    "Add one structured layer",
    "Choose a sharper shoe shape",
    "Try a single subtle accessory"
  ],
  "occasion_fit": "Conference-ready with one tweak.",
  "tailored_tip": "Build around pieces you already re-wear weekly."
}
```

Errors return a consistent shape, with a machine-readable code where one applies:

```json
{ "error": "No outfit detected. Please try again with a clear outfit photo.",
  "error_code": "NO_OUTFIT_DETECTED" }
```

| `error_code` | Status | Meaning |
|---|---|---|
| `NO_OUTFIT_DETECTED` | 422 | Photo has no clear outfit |
| `UNSUPPORTED_IMAGE_FORMAT` | 400 | Not a jpg/png/webp/heic, or undecodable |
| `IMAGE_TOO_LARGE` | 400 | Could not compress under the limit |
| `RATE_LIMITED` | 429 | Too many requests from one client |

---

## Campaign tracking

Every page preserves `campaign_id`, `source`, and `short_link_slug` from the URL:

```text
https://fitcheck.tailored-to-you.com/?campaign=fit_conf_london_a&source=qr&slug=fit-conf-london-a
```

The public QR points at a branded Short.io link that redirects there, so clicks are counted before the page even loads:

```text
Short.io link → Fit Check page → events logged → app CTA → Short.io app link → App Store
```

**Events logged:** `page_view`, `photo_selected`, `fit_check_started`, `fit_check_completed`, `email_submitted`, `app_cta_clicked`, `google_play_cta_clicked`, `logo_clicked`, `error`.

Each event row carries:

```text
timestamp · event_type · campaign_id · source · slug · occasion
environment · success · error_message · app_version
verdict_label · overall_score · fit_score · style_score · colour_score
```

Lead rows add `email` and `marketing_consent`. Emails are collected **only** on the lead endpoint, never in event rows.

---

## Configuration

See [`.env.example`](.env.example).

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes in prod | — | Blank locally → mock mode |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Vision-capable model |
| `APP_STORE_CTA_URL` | No | Short.io link | Surfaced via `/api/public-config` |
| `GOOGLE_SHEET_WEBHOOK_URL` | No | — | Blank → event logging no-ops |
| `ENVIRONMENT` | No | `local` | `local` enables mock mode |
| `MAX_UPLOAD_MB` | No | `5` | Compression target |
| `FIT_CHECK_RATE_LIMIT` | No | `8` | Fit Checks per window per client |
| `LEAD_RATE_LIMIT` | No | `5` | Lead submits per window per client |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Rate limit window |

---

## Security & privacy

This repo is public, so the guarantees are worth stating plainly:

* **The OpenAI key never leaves the backend.** `/api/public-config` exposes only the CTA URL, and a test asserts that.
* **Photos are never stored.** Held in memory, re-encoded, sent, discarded. Nothing is written to disk or logged.
* **No raw image data in logs.** Event rows carry campaign metadata only.
* **Email only with consent.** `/api/lead` rejects submissions without `marketing_consent`.
* **Uploads are validated and re-encoded** — content type and extension are checked, then the image is decoded and re-written as JPEG, which strips EXIF (including GPS) as a side effect.
* **Rate limited** per client on the two endpoints that cost money or write data.
* **Errors never leak internals.** All handlers return friendly messages; no stack traces reach the client.
* **Secrets are kept out of the image.** `.dockerignore` excludes `.env` and `.venv`, and the container runs as a non-root user.
* **CI guards it.** Every push fails the build if a `.env` is tracked or a credential pattern appears in a tracked file.

## Product guardrails

Fit Check feedback must be constructive, premium, concise, occasion-aware — and **never** body-critical or framed as attractiveness scoring. The system prompt in [`app/prompts.py`](app/prompts.py) forbids comments on body shape, weight, height, or attractiveness, and keeps the "fit" score about garment fit and cohesion rather than the wearer.

Scores are shown as `4/5` style sub-scores on outfit dimensions, not as a single "hot or not" rating.

---

## Deployment

Railway builds from the [`Dockerfile`](Dockerfile) and binds the platform port:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Push to `main` and Railway redeploys. Set the environment variables in the Railway dashboard — never in the repo.

## Project layout

```text
app/
  main.py              FastAPI routes, error handlers, rate-limit wiring
  config.py            Env-backed settings
  schemas.py           Pydantic request/response models
  prompts.py           System prompt and tone guardrails
  fit_check.py         OpenAI vision call + response parsing
  image_processing.py  Validate, resize, re-encode uploads
  event_logging.py     Fire-and-forget webhook logging
  rate_limit.py        In-memory per-client throttle
static/                index.html · result.html · app.js · result.js · styles.css
tests/                 Offline pytest suite
docs/images/           README screenshots
```

## Success metrics

Hero metric: **Fit Checks completed per 100 QR scans.**

Funnel: QR scan → photo upload → fit check completed → app CTA click / email submitted.

## License

[MIT](LICENSE)
