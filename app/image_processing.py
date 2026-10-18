from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener
except ImportError:  # pragma: no cover - dependency is installed in production.
    register_heif_opener = None


SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}
MAX_IMAGE_PIXELS = 20_000_000


class UnsupportedImageFormatError(Exception):
    pass


class ImageTooLargeError(Exception):
    pass


def _register_heif_support() -> None:
    if register_heif_opener is not None:
        register_heif_opener()


def _normalized_content_type(content_type: str, filename: str | None) -> str:
    lowered_type = (content_type or "").strip().lower()
    if lowered_type and lowered_type != "application/octet-stream":
        return lowered_type

    suffix = Path(filename or "").suffix.lower()
    return SUPPORTED_IMAGE_EXTENSIONS.get(suffix, lowered_type)


def _resize_dimensions(width: int, height: int, max_dimension: int) -> tuple[int, int]:
    largest_side = max(width, height)
    if largest_side <= max_dimension:
        return width, height

    scale = max_dimension / largest_side
    return max(1, int(width * scale)), max(1, int(height * scale))


def normalize_uploaded_image_bytes(
    image_bytes: bytes,
    content_type: str,
    filename: str | None,
    *,
    max_upload_mb: int,
) -> tuple[bytes, str]:
    resolved_type = _normalized_content_type(content_type, filename)
    if resolved_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "image/heif-sequence",
    }:
        raise UnsupportedImageFormatError

    _register_heif_support()

    try:
        with Image.open(BytesIO(image_bytes), formats=("JPEG", "PNG", "WEBP", "HEIF")) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ImageTooLargeError
            image = image.convert("RGB")
            for max_dimension in (1600, 1280):
                target_width, target_height = _resize_dimensions(image.width, image.height, max_dimension)
                resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

                try:
                    for quality in (82, 74, 66):
                        output = BytesIO()
                        resized.save(output, format="JPEG", quality=quality, optimize=True)
                        normalized_bytes = output.getvalue()
                        if len(normalized_bytes) <= max_upload_mb * 1024 * 1024:
                            return normalized_bytes, "image/jpeg"
                finally:
                    resized.close()
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedImageFormatError from exc

    raise ImageTooLargeError
