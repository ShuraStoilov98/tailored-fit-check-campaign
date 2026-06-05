const form = document.getElementById("fit-check-form");
const photoInput = document.getElementById("photo");
const occasionInput = document.getElementById("occasion-input");
const submitButton = document.getElementById("submit-button");
const uploadCard = document.getElementById("upload-card");
const uploadPreview = document.getElementById("upload-preview");
const errorState = document.getElementById("error");
const processingState = document.getElementById("processing-state");
const chips = Array.from(document.querySelectorAll(".chip"));
const brandLogo = document.getElementById("brand-logo");
const logoFallback = document.getElementById("logo-fallback");

const STORAGE_KEY = "fitCheckResult";

bindLogoFallback();
bindOccasionChips();
bindPhotoInput();

const params = new URLSearchParams(window.location.search);
const campaignContext = {
  campaign_id: params.get("campaign") || "",
  source: params.get("source") || "",
  short_link_slug: params.get("slug") || "",
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const file = photoInput.files?.[0];
  if (!file) {
    showError("Please choose a photo first.");
    return;
  }

  setLoading(true);

  try {
    const previewDataUrl = await toDataUrl(file);
    const formData = new FormData();
    formData.append("image", file);

    const occasion = occasionInput.value.trim();
    if (occasion) {
      formData.append("occasion", occasion);
    }
    if (campaignContext.campaign_id) {
      formData.append("campaign_id", campaignContext.campaign_id);
    }
    if (campaignContext.source) {
      formData.append("source", campaignContext.source);
    }
    if (campaignContext.short_link_slug) {
      formData.append("slug", campaignContext.short_link_slug);
    }

    const response = await fetch("/api/fit-check", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Could not generate your Fit Check right now.");
    }

    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        result: payload,
        image_preview: previewDataUrl,
        selected_occasion: occasion,
        campaign_context: campaignContext,
      })
    );

    const resultUrl = new URL("/result", window.location.origin);
    if (campaignContext.campaign_id) {
      resultUrl.searchParams.set("campaign", campaignContext.campaign_id);
    }
    if (campaignContext.source) {
      resultUrl.searchParams.set("source", campaignContext.source);
    }
    if (campaignContext.short_link_slug) {
      resultUrl.searchParams.set("slug", campaignContext.short_link_slug);
    }

    window.location.assign(resultUrl.toString());
  } catch (error) {
    const message = error instanceof Error ? error.message : "Something went wrong. Please try again.";
    showError(message);
  } finally {
    setLoading(false);
  }
});

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  processingState.classList.toggle("hidden", !isLoading);
}

function showError(message) {
  errorState.textContent = message;
  errorState.classList.remove("hidden");
}

function clearError() {
  errorState.textContent = "";
  errorState.classList.add("hidden");
}

function bindOccasionChips() {
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((item) => {
        item.classList.remove("active");
        item.setAttribute("aria-checked", "false");
      });

      chip.classList.add("active");
      chip.setAttribute("aria-checked", "true");
      occasionInput.value = chip.dataset.value || "";
    });
  });
}

function bindPhotoInput() {
  photoInput.addEventListener("change", () => {
    const file = photoInput.files?.[0];
    if (!file) {
      submitButton.disabled = true;
      uploadCard.classList.remove("has-preview");
      uploadPreview.src = "";
      return;
    }

    submitButton.disabled = false;

    const reader = new FileReader();
    reader.onload = (e) => {
      uploadPreview.src = String(e.target?.result || "");
      uploadCard.classList.add("has-preview");
    };
    reader.readAsDataURL(file);
  });
}

function bindLogoFallback() {
  if (!brandLogo) {
    return;
  }

  brandLogo.addEventListener("error", () => {
    brandLogo.classList.add("hidden");
    logoFallback.classList.remove("hidden");
  });
}

function toDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      resolve(String(reader.result || ""));
    };
    reader.onerror = () => {
      reject(new Error("Could not read the image preview."));
    };
    reader.readAsDataURL(file);
  });
}

