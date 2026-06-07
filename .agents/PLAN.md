# PLAN.md

Build plan for Tailored Fit Check Campaign v1.

## Objective

Launch a lightweight mobile web Fit Check experience for organic campaign testing.

The campaign experience:

```text
Scan QR
→ upload/take outfit photo
→ get AI Fit Check verdict
→ download Tailored app or join early community
```

The v1 should be good enough for real-world testing in London conferences, London street activations, Instagram, TikTok, Pinterest, LinkedIn, and warm-network sharing.

## Phase 0 — Repo Setup

Goal: clean project skeleton.

Tasks:

* [x] Create GitHub repo: `tailored-fit-check-campaign`
* [x] Add README.md
* [x] Add AGENTS.md
* [x] Add PLAN.md
* [x] Add `.gitignore`
* [x] Add `.env.example`
* [x] Add `requirements.txt`
* [x] Add `Dockerfile`
* [x] Add base folders: `app/`, `static/`, `tests/`

Acceptance criteria:

* Repo is private.
* Repo has clear documentation.
* No secrets are committed.

## Phase 1 — Local App Skeleton

Goal: local app runs with static frontend and health route.

Tasks:

* [x] Implement FastAPI app in `app/main.py`
* [x] Serve `static/index.html` at `/`
* [x] Add `/health` route
* [x] Add basic config loading from environment variables
* [x] Add minimal CSS and JS files
* [x] Add local run instructions

Acceptance criteria:

* `uvicorn app.main:app --reload` works.
* `http://localhost:8000` loads the landing page.
* `http://localhost:8000/health` returns OK.

## Phase 2 — Frontend v1

Goal: mobile-first Fit Check UI.

Tasks:

* [x] Create landing headline and explanation
* [x] Add photo upload / camera capture input
* [x] Add optional occasion selector
* [x] Add “Get my Fit Check” button
* [x] Add loading state
* [x] Add result card layout
* [x] Add app download CTA
* [x] Add email capture CTA after result
* [x] Preserve campaign parameters from URL

Suggested landing copy:

```text
Free AI Fit Check

Get an instant outfit verdict and 3 styling improvements.
No app needed.
```

Suggested CTA:

```text
Get my Fit Check
```

Acceptance criteria:

* Page works on mobile.
* User can select/take photo.
* UI does not feel cluttered.
* Campaign ID is available to JS.

## Phase 3 — Fit Check API

Goal: backend accepts image and returns structured result.

Tasks:

* [x] Add `POST /api/fit-check`
* [x] Validate image file type
* [x] Validate image size
* [x] Accept optional occasion and campaign ID
* [x] Add OpenAI vision call
* [x] Add structured response schema
* [x] Add friendly error handling
* [x] Ensure uploaded photos are not stored

Response shape:

```json
{
  "verdict_label": "Strong base",
  "one_line_verdict": "The outfit works well, with one sharper finishing touch.",
  "what_works": [
    "The colour palette feels cohesive.",
    "The silhouette is balanced."
  ],
  "improvements": [
    "Add one sharper finishing touch.",
    "Use a cleaner shoe shape.",
    "Consider a more structured layer."
  ],
  "occasion_fit": "Good for casual work or daytime events.",
  "tailored_tip": "Daily fit checks help you learn what you actually wear and love."
}
```

Acceptance criteria:

* API returns valid JSON.
* Result renders on frontend.
* No photo is stored.
* Errors are clear and non-technical.

## Phase 4 — Prompt Tuning

Goal: make output feel premium and safe.

Tasks:

* [x] Create system prompt in `app/prompts.py`
* [x] Keep feedback outfit-focused
* [x] Avoid body comments
* [x] Avoid harsh ratings
* [x] Avoid numerical scores
* [x] Return concise, structured JSON
* [x] Test with at least 20 outfit images

Verdict labels to use:

```text
Polished
Strong base
Almost there
Needs one sharper finishing touch
Great casual fit
Conference-ready with one tweak
```

Acceptance criteria:

* Feedback feels useful.
* Feedback is not judgemental.
* Feedback is concise enough for mobile.

## Phase 5 — Event Logging

Goal: capture campaign analytics.

Tasks:

* [x] Add `POST /api/event`
* [x] Add event logging helper
* [x] Log events to Google Sheet webhook or temporary backend logs
* [x] Include campaign ID, event type, timestamp
* [x] Log frontend events:

  * [x] page_view
  * [x] photo_selected
  * [x] fit_check_started
  * [x] fit_check_completed
  * [x] app_cta_clicked
  * [x] email_submitted
  * [x] error

Acceptance criteria:

* Each key step is logged.
* Logs include campaign ID.
* Logging failure does not break the user experience.

## Phase 6 — Lead Capture

Goal: collect emails after the user receives value.

Tasks:

* [x] Add email input after result
* [x] Add explicit marketing consent checkbox
* [x] Add `POST /api/lead`
* [x] Validate email format
* [x] Log lead to Google Sheet or email tool
* [x] Show confirmation message

Suggested copy:

```text
Want daily Fit Checks and early access to new Tailored features?
Join the early community.
```

Acceptance criteria:

* Email capture happens after result.
* Consent is explicit.
* User receives confirmation.
* No pre-ticked marketing consent.

## Phase 7 — Railway Deployment

Goal: deploy live v1.

Tasks:

* [x] Add Dockerfile
* [x] Connect GitHub repo to Railway
* [x] Set Railway environment variables
* [x] Deploy
* [x] Verify `/health`
* [x] Verify homepage
* [x] Verify fit check flow
* [x] Test from mobile

Required environment variables:

```text
OPENAI_API_KEY=
APP_STORE_CTA_URL=
GOOGLE_SHEET_WEBHOOK_URL=
ENVIRONMENT=production
MAX_UPLOAD_MB=5
```

Acceptance criteria:

* Railway URL works.
* Fit Check works from mobile.
* Secrets are set in Railway, not committed.

## Phase 8 — Tracking Links

Goal: connect Short.io and App Store campaign tracking.

Tasks:

* [x] Create Short.io entry link for campaign
* [x] Destination points to Railway URL with campaign parameter
* [x] Generate QR code from Short.io
* [x] Create post-result app CTA Short.io link
* [x] App CTA link points to Apple Campaign Link
* [x] Test Short.io click analytics

Example links:

```text
go.tailored-to-you.com/fit-test-a
go.tailored-to-you.com/fit-conf-london-a
go.tailored-to-you.com/fit-street-london-a
go.tailored-to-you.com/fit-app-conf-a
```

Acceptance criteria:

* QR scan is tracked in Short.io.
* App CTA click is tracked in Short.io.
* Campaign ID is present in app logs.

## Phase 9 — Internal Testing

Goal: make sure it is safe for public testing.

Tasks:

* [x] Test 20 outfit images
* [ ] Test poor lighting
* [ ] Test large image file
* [ ] Test unsupported file type
* [x] Test no occasion selected
* [x] Test app CTA
* [x] Test email submission
* [x] Test mobile Safari
* [ ] Test mobile Chrome
* [x] Test QR scan from phone

Acceptance criteria:

* No obvious broken path.
* Results feel brand-safe.
* Tracking works.
* Public test can start.

## Phase 10 — Public PoC

Goal: run first campaign and learn.

Initial campaigns:

```text
fit_test_wa
fit_ig_reel_a
fit_conf_london_a
fit_street_london_a
```

Review metrics:

```text
QR scans
page views
photo uploads
fit checks completed
email submissions
app CTA clicks
completion rate
qualitative comments
```

Decision options:

```text
Scale
Retest
Rewrite
Kill
Move to paid
```

Hero metric:

```text
Fit checks completed per 100 QR scans
```

## Out of Scope for v1

Do not build yet:

* User accounts
* Firebase Auth
* Wardrobe database
* Saved fit history
* Payments
* Subscription gates
* Full analytics dashboard
* Admin panel
* App integration
* Photo storage
* Social sharing
* Multi-language support

## v2 Ideas

Only consider after v1 signal:

* Save Fit Check history with user consent
* “Send result to email”
* Social share card
* Referral link
* Daily reminder
* Wardrobe item extraction
* Firebase integration
* App deep link after download
* Better analytics dashboard
* Creator-specific campaign pages
