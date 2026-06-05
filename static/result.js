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
