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
let selectedPreviewUrl = "";

const STORAGE_KEY = "fitCheckResult";
const NO_OUTFIT_ERROR_CODE = "NO_OUTFIT_DETECTED";
const IMAGE_TOO_LARGE_ERROR_CODE = "IMAGE_TOO_LARGE";
const UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE = "UNSUPPORTED_IMAGE_FORMAT";
const IMAGE_NORMALIZATION_FAILED = "IMAGE_NORMALIZATION_FAILED";
const TARGET_UPLOAD_BYTES = 4 * 1024 * 1024;
const MAX_BACKEND_BYTES = 5 * 1024 * 1024;
const IS_LOCAL_DEV = ["localhost", "127.0.0.1"].includes(window.location.hostname);

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
      error_message: extra.error_message || "",
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
    const normalizedImage = await normalizeImageFile(file);
    const formData = new FormData();
    formData.append("image", normalizedImage.file, "outfit.jpg");

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
        image_preview: normalizedImage.previewUrl || selectedPreviewUrl,
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
    handleSubmissionError(error);
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

  if (errorCode === IMAGE_TOO_LARGE_ERROR_CODE) {
    showRetryModal(
      "Photo too large",
      "Please try a screenshot or a smaller image."
    );
    return;
  }

  if (errorCode === UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE) {
    resetCapturePhoto();
    showRetryModal(
      "Photo format not supported",
      "Please take a new photo or choose a JPEG/PNG image."
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
      clearError();

      toDataUrl(file)
        .then((previewUrl) => {
          selectedPreviewUrl = previewUrl;
          renderPreview(previewUrl);
        })
        .catch(() => {
          selectedPreviewUrl = "";
          uploadCard.classList.remove("has-preview");
          uploadPreview.src = "";
        });
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
  selectedPreviewUrl = "";
  submitButton.disabled = true;
  uploadCard.classList.remove("has-preview");
  uploadPreview.src = "";
}

function renderPreview(previewUrl) {
  uploadPreview.src = previewUrl;
  uploadCard.classList.add("has-preview");
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

function createUploadError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function logNormalizationFailure(code) {
  logEvent("error", { error_message: code });
}

async function normalizeImageFile(file) {
  const decodedImage = await decodeImageForCanvas(file).catch(() => {
    throw createUploadError(
      UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE,
      "Please take a new photo or choose a screenshot/JPEG image."
    );
  });

  try {
    let fallbackBlob = null;

    for (const maxDimension of [1600, 1280]) {
      const { width, height } = getScaledDimensions(
        decodedImage.width,
        decodedImage.height,
        maxDimension
      );
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;

      const context = canvas.getContext("2d", { alpha: false });
      if (!context) {
        throw createUploadError(
          IMAGE_NORMALIZATION_FAILED,
          "We couldn't prepare this photo. Please try another image."
        );
      }

      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, width, height);
      context.drawImage(decodedImage.source, 0, 0, width, height);

      for (const quality of [0.82, 0.74, 0.66]) {
        const blob = await canvasToBlob(canvas, "image/jpeg", quality);
        if (!blob) continue;

        if (!fallbackBlob || blob.size < fallbackBlob.size) {
          fallbackBlob = blob;
        }

        if (blob.size <= TARGET_UPLOAD_BYTES) {
          return buildNormalizedImageResult(file, blob);
        }
      }
    }

    if (fallbackBlob && fallbackBlob.size <= MAX_BACKEND_BYTES) {
      return buildNormalizedImageResult(file, fallbackBlob);
    }

    throw createUploadError(
      IMAGE_TOO_LARGE_ERROR_CODE,
      "Please try a screenshot or a smaller image."
    );
  } finally {
    cleanupDecodedImage(decodedImage);
  }
}

async function buildNormalizedImageResult(file, blob) {
  const previewUrl = await toDataUrl(blob);

  if (IS_LOCAL_DEV) {
    console.info("Image normalized", {
      originalType: file.type || "unknown",
      originalSize: file.size,
      normalizedSize: blob.size,
      outputType: "image/jpeg",
    });
  }

  return {
    file: blob,
    previewUrl,
    contentType: "image/jpeg",
    originalType: file.type || "",
    originalSize: file.size,
    normalizedSize: blob.size,
  };
}

async function decodeImageForCanvas(file) {
  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file);
      return {
        width: bitmap.width,
        height: bitmap.height,
        source: bitmap,
        cleanup: () => bitmap.close(),
      };
    } catch (error) {
      // Fall through to HTMLImageElement decoding.
    }
  }

  return decodeWithImageElement(file);
}

function decodeWithImageElement(file) {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
      resolve({
        width: image.naturalWidth,
        height: image.naturalHeight,
        source: image,
        cleanup: () => URL.revokeObjectURL(objectUrl),
      });
    };

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Unsupported image format."));
    };

    image.src = objectUrl;
  });
}

function cleanupDecodedImage(decodedImage) {
  if (decodedImage?.cleanup) {
    decodedImage.cleanup();
  }
}

function getScaledDimensions(width, height, maxDimension) {
  const largestSide = Math.max(width, height);
  if (!largestSide || largestSide <= maxDimension) {
    return { width, height };
  }

  const scale = maxDimension / largestSide;
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
        return;
      }

      reject(new Error("Could not create image blob."));
    }, type, quality);
  });
}

function handleSubmissionError(error) {
  const errorCode = typeof error?.code === "string" ? error.code : "";
  if (errorCode === UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE) {
    logNormalizationFailure(UNSUPPORTED_IMAGE_FORMAT_ERROR_CODE);
    resetCapturePhoto();
    showRetryModal(
      "Photo format not supported",
      "Please take a new photo or choose a screenshot/JPEG image."
    );
    return;
  }

  if (errorCode === IMAGE_TOO_LARGE_ERROR_CODE) {
    logNormalizationFailure(IMAGE_TOO_LARGE_ERROR_CODE);
    showRetryModal(
      "Photo too large",
      "Please try a screenshot or a smaller image."
    );
    return;
  }

  if (errorCode === IMAGE_NORMALIZATION_FAILED) {
    logNormalizationFailure(IMAGE_NORMALIZATION_FAILED);
    showRetryModal(
      "Fit Check unavailable",
      "We couldn't prepare your photo just now. Please try again with another image."
    );
    return;
  }

  showRetryModal(
    "Fit Check unavailable",
    "We couldn't complete your Fit Check just now. Please try again in a moment."
  );
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
