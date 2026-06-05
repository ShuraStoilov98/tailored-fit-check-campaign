# AGENTS.md

Instructions for AI coding agents working on this repository.

## Project Context

This repository contains a lightweight campaign web app for Tailored.

Tailored is a fashion app that helps users wear more of what they already own, buy only what truly adds value, and build a more intentional wardrobe habit.

This specific project is not the main Tailored app. It is a separate growth experiment for “Daily Fit Check” campaigns. Users scan a QR code, upload or take an outfit photo, receive a short AI Fit Check verdict, and are invited to download the app or join the early community.

## Core Goal

Build a simple, reliable v1 that can be deployed quickly and used in real-world London street/conference campaigns.

The goal is not architectural perfection. The goal is a clean, safe, trackable MVP.

## Non-Negotiables

1. Do not require login or Firebase Auth.
2. Do not connect to the main Tailored production database.
3. Do not store uploaded photos in v1.
4. Do not expose the OpenAI API key to the frontend.
5. Do not add unnecessary frameworks or complexity.
6. Do not make the experience feel like “hot or not” or outfit shaming.
7. Keep all feedback outfit-focused, constructive, and premium.
8. Keep the app mobile-first.
9. Keep the code simple enough for founders to maintain.

## Preferred Architecture

Single-service app:

```text
FastAPI backend
+ static frontend served from /static
+ OpenAI vision call from backend only
+ campaign/event logging
+ Railway deployment
```

Preferred structure:

```text
app/
  main.py
  config.py
  schemas.py
  prompts.py
  fit_check.py
  event_logging.py
  security.py

static/
  index.html
  styles.css
  app.js
```

## Backend Guidelines

Use FastAPI.

Required routes for v1:

```text
GET /
GET /health
POST /api/fit-check
POST /api/lead
POST /api/event
```

`POST /api/fit-check` should accept:

```text
image file
occasion optional
campaign_id optional
source optional
```

It should return structured JSON:

```json
{
  "verdict_label": "Strong base",
  "one_line_verdict": "The outfit works well, with one sharper finishing touch.",
  "what_works": ["..."],
  "improvements": ["...", "...", "..."],
  "occasion_fit": "...",
  "tailored_tip": "..."
}
```

## Frontend Guidelines

Keep frontend simple:

* Plain HTML, CSS, and JavaScript.
* No React/Vite unless explicitly requested.
* Mobile-first layout.
* Clear CTA.
* Premium Tailored tone.
* Upload/take photo support.
* Loading state while verdict is generated.
* Result card.
* App download CTA.
* Email capture CTA after result.

## Fit Check Tone

The AI should sound like a premium, kind personal stylist.

Do:

```text
The proportions feel balanced.
A sharper shoe shape would make the outfit feel more intentional.
A structured layer would elevate this for a conference setting.
```

Do not:

```text
This is unflattering.
Your body shape does not suit this.
This outfit is bad.
You look bigger/smaller/shorter.
```

Avoid body comments. Focus on clothes, silhouette, colour, occasion fit, polish, and styling choices.

## Privacy and Data

For v1:

* Do not save photos.
* Do not persist images to disk except temporary request handling.
* Do not log raw image data.
* Do not log personally identifiable data except email when the user submits it.
* Include `marketing_consent` when collecting emails.
* Keep event logs lightweight.

## Campaign Tracking

Every page/session should preserve:

```text
campaign_id
source
short_link_slug
```

These may come from URL parameters, for example:

```text
?campaign=fit_conf_london_a&source=qr&slug=fit-conf-london-a
```

Events to log:

```text
page_view
photo_selected
fit_check_started
fit_check_completed
email_submitted
app_cta_clicked
error
```

## Security / Abuse Prevention

Implement basic protections:

* Max image size from env var, default 5 MB.
* Accept only jpg, jpeg, png, webp.
* Basic rate limiting if easy.
* Friendly error messages.
* Timeouts around AI calls.
* Never expose secrets in frontend.
* Validate email format before submission.

## Dependencies

Prefer a small dependency set.

Expected backend dependencies:

```text
fastapi
uvicorn
python-multipart
pydantic-settings
openai
httpx
```

Only add more if there is a clear reason.

## Deployment

Target: Railway.

The app must run on the port provided by Railway:

```text
$PORT
```

Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Development Style

* Keep functions small and readable.
* Use clear names.
* Add comments only where they clarify non-obvious choices.
* Avoid over-engineering.
* Prefer explicit simple code over clever abstractions.
* Keep the founders able to edit copy, prompts, and styling easily.

## Before Marking Work Complete

Check:

1. App runs locally.
2. `/health` returns OK.
3. Landing page loads.
4. Image upload works.
5. Fit Check returns structured output.
6. Error states are user-friendly.
7. App CTA works.
8. Email capture works or gracefully degrades.
9. No secrets are committed.
10. README remains accurate.
