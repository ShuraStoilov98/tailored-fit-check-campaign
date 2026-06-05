# Tailored Fit Check Campaign

Lightweight web campaign app for Tailored AI Fit Check QR experiments.

This project powers a no-login, no-app-download Fit Check experience used for Tailored organic marketing campaigns, street activations, conference activations, and social media experiments.

Users scan a Tailored QR code, upload or take an outfit photo, receive a short AI Fit Check verdict, and are then invited to download the Tailored app or join the early community.

## Purpose

Tailored’s core app helps users build a smarter wardrobe habit over time. This campaign app tests one specific growth loop:

1. Give users instant value through a 30-second Fit Check.
2. Use that moment to communicate the Tailored promise.
3. Track which channels, locations, hooks, and messages drive engagement.
4. Convert high-intent users into app downloads or email signups.

This app is deliberately separate from the main Tailored app and backend. It does not require Firebase Auth, user profiles, wardrobe upload, or production app integration.

## User Flow

```text
Short.io QR link
→ Fit Check landing page
→ User uploads / takes outfit photo
→ User optionally selects occasion
→ AI returns Fit Check verdict
→ User sees app download CTA and email/community CTA
→ Events are logged for campaign analysis
```

## Core Features for v1

* Mobile-first landing page.
* Upload or take outfit photo.
* Optional occasion selector.
* AI-generated Fit Check verdict.
* Short, constructive styling suggestions.
* App Store CTA.
* Email capture CTA.
* Basic event logging.
* Campaign ID tracking through URL parameters.
* No user account required.
* No photo storage in v1.

## Example Campaign URL

```text
https://fitcheck-tailored.up.railway.app/?campaign=fit_conf_london_a
```

The public QR should point to a branded Short.io link, for example:

```text
https://go.tailored-to-you.com/fit-conf-london-a
```

which redirects to the campaign page above.

## Tracking Flow

```text
Short.io entry link
→ Railway Fit Check page
→ Fit Check events logged
→ Post-verdict app CTA
→ Short.io app download link
→ Apple Campaign Link
→ App Store
```

Short.io is used for immediate click tracking. App Store Connect campaign links are used for later download attribution when enough installs are generated.

## Suggested Events

The app should log the following events:

```text
page_view
photo_selected
fit_check_started
fit_check_completed
email_submitted
app_cta_clicked
error
```

Each event should include:

```text
timestamp
campaign_id
event_type
occasion
device_type
short_link_slug
result_generated
email
marketing_consent
error_message
```

## Privacy Principles

For v1:

* Do not store uploaded outfit photos.
* Process the photo only to generate the Fit Check result.
* Store only lightweight campaign analytics.
* Collect email only after value has been delivered.
* Require explicit marketing consent before sending marketing emails.
* Keep feedback outfit-focused, not body-focused.

## Tech Stack

* Backend: FastAPI
* Frontend: Static HTML, CSS, JavaScript
* Hosting: Railway
* AI: OpenAI vision model
* Tracking: Short.io, App Store Connect campaign links, Google Sheet export/logging
* Deployment: Dockerfile via Railway

## Local Development

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

## Environment Variables

See `.env.example`.

Required for v1:

```text
OPENAI_API_KEY=
APP_STORE_CTA_URL=
GOOGLE_SHEET_WEBHOOK_URL=
ENVIRONMENT=local
MAX_UPLOAD_MB=5
```

## Deployment

The preferred v1 deployment target is Railway.

Railway should build from the Dockerfile and run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Product Guardrails

Fit Check feedback must be:

* Constructive.
* Premium and concise.
* Outfit-focused.
* Occasion-aware.
* Never body-critical.
* Never framed as attractiveness scoring.
* Never harsh, mocking, or absolute.

Avoid numerical ratings like `7/10` in v1. Use verdict labels such as:

```text
Polished
Strong base
Almost there
Needs one sharper finishing touch
Great casual fit
Conference-ready with one tweak
```

## Success Metrics

The campaign is successful if it produces evidence of real-world pull.

Primary metrics:

```text
QR scans
photo uploads
fit checks completed
email submissions
app CTA clicks
```

Key conversion rates:

```text
QR scan → photo upload
photo upload → fit check completed
fit check completed → app CTA click
fit check completed → email submitted
```

Hero metric:

```text
Fit checks completed per 100 QR scans
```
