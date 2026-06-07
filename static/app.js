const form = document.getElementById("fit-check-form");
const photoInput = document.getElementById("photo");
const cameraInput = document.getElementById("photo-camera");
const occasionInput = document.getElementById("occasion-input");
const submitButton = document.getElementById("submit-button");
const uploadCard = document.getElementById("upload-card");
const uploadPreview = document.getElementById("upload-preview");
const errorState = document.getElementById("error");
const processingState = document.getElementById("processing-state");
const chips = Array.from(document.querySelectorAll(".chip"));
const brandLogo = document.getElementById("brand-logo");
const logoFallback = document.getElementById("logo-fallback");
const pickerOverlay = document.getElementById("photo-picker-overlay");
const pickerCameraBtn = document.getElementById("picker-camera");
const pickerGalleryBtn = document.getElementById("picker-gallery");
const modalState = createModal();

let selectedFile = null;

const STORAGE_KEY = "fitCheckResult";
const NO_OUTFIT_ERROR_CODE = "NO_OUTFIT_DETECTED";

bindLogoFallback();
bindOccasionChips();
bindPhotoInputs();
bindPhotoPicker();

const params = new URLSearchParams(window.location.search);
const campaignContext = {
  campaign_id: params.get("campaign") || "",
  source: params.get("source") || "",
  short_link_slug: params.get("slug") || "",
};

function logEvent(eventType, extra = {}) {
  fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_type: eventType,
      campaign_id: campaignContext.campaign_id,
      source: campaignContext.source,
      slug: campaignContext.short_link_slug,
      occasion: extra.occasion || "",
    }),
  }).catch(() => {});
}

logEvent("page_view");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const file = selectedFile;
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
      handleFitCheckError(payload);
      return;
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
    showRetryModal(
      "Fit Check unavailable",
      "We couldn't complete your Fit Check just now. Please try again in a moment."
    );
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

function handleFitCheckError(payload) {
  const errorCode = typeof payload?.error_code === "string" ? payload.error_code : "";
  if (errorCode === NO_OUTFIT_ERROR_CODE) {
    resetCapturePhoto();
    showRetryModal(
      "No outfit detected",
      "Please try again with a clear outfit photo."
    );
    return;
  }

  showRetryModal(
    "Fit Check unavailable",
    "We couldn't complete your Fit Check just now. Please try again in a moment."
  );
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

function bindPhotoInputs() {
  [photoInput, cameraInput].forEach((input) => {
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return;
      selectedFile = file;
      submitButton.disabled = false;
      logEvent("photo_selected");

      const reader = new FileReader();
      reader.onload = (e) => {
        uploadPreview.src = String(e.target?.result || "");
        uploadCard.classList.add("has-preview");
      };
      reader.readAsDataURL(file);
    });
  });
}

function bindPhotoPicker() {
  uploadCard.addEventListener("click", (e) => {
    e.preventDefault();
    openPhotoPicker();
  });

  uploadCard.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPhotoPicker();
    }
  });

  pickerCameraBtn.addEventListener("click", () => {
    closePhotoPicker();
    cameraInput.click();
  });

  pickerGalleryBtn.addEventListener("click", () => {
    closePhotoPicker();
    photoInput.click();
  });

  pickerOverlay.addEventListener("click", (e) => {
    if (e.target === pickerOverlay) closePhotoPicker();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !pickerOverlay.classList.contains("hidden")) {
      closePhotoPicker();
    }
  });
}

function openPhotoPicker() {
  pickerOverlay.classList.remove("hidden");
  document.body.classList.add("modal-open");
  pickerCameraBtn.focus();
}

function closePhotoPicker() {
  pickerOverlay.classList.add("hidden");
  document.body.classList.remove("modal-open");
  uploadCard.focus();
}

function resetCapturePhoto() {
  photoInput.value = "";
  cameraInput.value = "";
  selectedFile = null;
  submitButton.disabled = true;
  uploadCard.classList.remove("has-preview");
  uploadPreview.src = "";
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

function createModal() {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay hidden";
  overlay.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title" aria-describedby="modal-body">
      <p id="modal-title" class="modal-title"></p>
      <p id="modal-body" class="modal-body"></p>
      <button type="button" class="primary-btn modal-button">Try again</button>
    </div>
  `;

  const title = overlay.querySelector("#modal-title");
  const body = overlay.querySelector("#modal-body");
  const button = overlay.querySelector(".modal-button");

  button.addEventListener("click", closeModal);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !overlay.classList.contains("hidden")) {
      closeModal();
    }
  });

  document.body.appendChild(overlay);
  return { overlay, title, body, button };
}

function showRetryModal(title, body) {
  clearError();
  processingState.classList.add("hidden");
  modalState.title.textContent = title;
  modalState.body.textContent = body;
  modalState.overlay.classList.remove("hidden");
  document.body.classList.add("modal-open");
  modalState.button.focus();
}

function closeModal() {
  modalState.overlay.classList.add("hidden");
  document.body.classList.remove("modal-open");
  uploadCard.focus();
}
