const STORAGE_KEY = "fitCheckResult";

const params = new URLSearchParams(window.location.search);
const campaignContext = {
  campaign_id: params.get("campaign") || "",
  source: params.get("source") || "",
  short_link_slug: params.get("slug") || "",
};

const brandLogo = document.getElementById("brand-logo");
const logoFallback = document.getElementById("logo-fallback");
const resultImage = document.getElementById("result-image");
const lookLabel = document.getElementById("look-label");
const overallScoreEl = document.getElementById("overall-score");
const overallScoreFill = document.getElementById("overall-score-fill");
const fitScoreEl = document.getElementById("fit-score");
const styleScoreEl = document.getElementById("style-score");
const colourScoreEl = document.getElementById("colour-score");
const whatWorksBlock = document.getElementById("what-works");
const improvementsBlock = document.getElementById("improvements");
const appCta = document.getElementById("app-cta");
const leadForm = document.getElementById("lead-form");
const leadEmailInput = document.getElementById("lead-email");
const leadConsentCheckbox = document.getElementById("lead-consent-checkbox");
const leadSubmitBtn = document.getElementById("lead-submit");
const leadMsg = document.getElementById("lead-msg");

let _parsed = null;

function logEvent(eventType) {
  fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_type: eventType,
      campaign_id: campaignContext.campaign_id,
      source: campaignContext.source,
      slug: campaignContext.short_link_slug,
    }),
  }).catch(() => {});
}

appCta.addEventListener("click", () => logEvent("app_cta_clicked"));

bindLogoFallback();

const stored = sessionStorage.getItem(STORAGE_KEY);
if (!stored) {
  redirectHome();
} else {
  hydrateResult(stored);
}

function hydrateResult(rawValue) {
  let parsed;
  try {
    parsed = JSON.parse(rawValue);
  } catch {
    redirectHome();
    return;
  }

  if (!parsed?.image_preview || !parsed?.result) {
    redirectHome();
    return;
  }

  _parsed = parsed;
  const r = parsed.result;

  resultImage.src = parsed.image_preview;
  lookLabel.textContent = deriveLookLabel(parsed.selected_occasion, r.verdict_label);

  const overall = r.overall_score ?? 4;
  const max = 5;
  overallScoreEl.textContent = `${overall}/${max}`;
  overallScoreFill.style.width = `${(overall / max) * 100}%`;
  overallScoreFill.closest("[role='progressbar']").setAttribute("aria-valuenow", String(overall));

  if (fitScoreEl) fitScoreEl.textContent = String(r.fit_score ?? 4);
  if (styleScoreEl) styleScoreEl.textContent = String(r.style_score ?? 3);
  if (colourScoreEl) colourScoreEl.textContent = String(r.colour_score ?? 4);

  renderBullets(whatWorksBlock, r.what_works || [], [
    "Balanced base",
    "Palette feels cohesive",
  ], 2);

  renderBullets(improvementsBlock, r.improvements || [], [
    "Add one sharper finishing touch",
    "Choose cleaner shoe lines",
    "Use one subtle accessory",
  ], 3);

  setCtaHref(parsed.campaign_context || campaignContext);
  applyPublicConfig();
}

function renderBullets(container, items, defaults, count) {
  const merged = [...items, ...defaults].slice(0, count);
  container.innerHTML = "";
  merged.forEach((item) => {
    const el = document.createElement("div");
    el.className = "result-bullet";
    el.textContent = item;
    container.appendChild(el);
  });
}

function deriveLookLabel(occasion, verdict) {
  if (occasion === "Conference") return "Conference-ready base";
  if (occasion === "Work") return "Polished work look";
  if (verdict && verdict.toLowerCase().includes("casual")) return "Clean casual look";
  return "Bold everyday fit";
}

function setCtaHref(context) {
  const ctaUrl = new URL(appCta.getAttribute("href"), window.location.origin);
  if (context.campaign_id) ctaUrl.searchParams.set("campaign", context.campaign_id);
  if (context.source) ctaUrl.searchParams.set("source", context.source);
  if (context.short_link_slug) ctaUrl.searchParams.set("slug", context.short_link_slug);
  appCta.setAttribute("href", ctaUrl.toString());
}

async function applyPublicConfig() {
  try {
    const response = await fetch("/api/public-config");
    if (!response.ok) return;
    const payload = await response.json();
    const value = String(payload.app_store_cta_url || "").trim();
    if (!value) return;

    const baseUrl = new URL(value, window.location.origin);
    const currentUrl = new URL(appCta.getAttribute("href"), window.location.origin);
    currentUrl.searchParams.forEach((v, k) => baseUrl.searchParams.set(k, v));
    appCta.setAttribute("href", baseUrl.toString());
  } catch {
    // Keep existing CTA if public config is unavailable.
  }
}

function bindLogoFallback() {
  if (!brandLogo) return;
  brandLogo.addEventListener("error", () => {
    brandLogo.classList.add("hidden");
    logoFallback.classList.remove("hidden");
  });
}

function redirectHome() {
  const homeUrl = new URL("/", window.location.origin);
  if (campaignContext.campaign_id) homeUrl.searchParams.set("campaign", campaignContext.campaign_id);
  if (campaignContext.source) homeUrl.searchParams.set("source", campaignContext.source);
  if (campaignContext.short_link_slug) homeUrl.searchParams.set("slug", campaignContext.short_link_slug);
  window.location.replace(homeUrl.toString());
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function showLeadMsg(text, type) {
  leadMsg.textContent = text;
  leadMsg.className = `lead-message ${type}`;
}

function clearLeadMsg() {
  leadMsg.textContent = "";
  leadMsg.className = "lead-message hidden";
}

leadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearLeadMsg();

  const email = leadEmailInput.value.trim();
  if (!isValidEmail(email)) {
    showLeadMsg("Please enter a valid email.", "error");
    return;
  }
  if (!leadConsentCheckbox.checked) {
    showLeadMsg("Please confirm you're happy to receive Tailored updates.", "error");
    return;
  }

  leadSubmitBtn.disabled = true;
  leadSubmitBtn.textContent = "Joining...";

  const ctx = _parsed?.campaign_context || campaignContext;
  const r = _parsed?.result || {};

  try {
    const response = await fetch("/api/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        marketing_consent: true,
        campaign_id: ctx.campaign_id || "",
        source: ctx.source || "",
        slug: ctx.short_link_slug || "",
        occasion: _parsed?.selected_occasion || "",
        verdict_label: r.verdict_label || "",
        overall_score: r.overall_score ?? null,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "We couldn't save your email just now. Please try again.");
    }

    leadEmailInput.disabled = true;
    leadConsentCheckbox.disabled = true;
    leadSubmitBtn.disabled = true;
    leadSubmitBtn.textContent = "Joined";
    showLeadMsg("You're in — welcome to the early Tailored community.", "success");
  } catch (err) {
    const message = err instanceof Error ? err.message : "We couldn't save your email just now. Please try again.";
    showLeadMsg(message, "error");
    leadSubmitBtn.disabled = false;
    leadSubmitBtn.textContent = "Join the community";
  }
});
