"""Image normalisation: the only place uploaded bytes are touched."""

from io import BytesIO

import pytest
from PIL import Image

from app.image_processing import (
    ImageTooLargeError,
    UnsupportedImageFormatError,
    normalize_uploaded_image_bytes,
)


def _image_bytes(width: int, height: int, fmt: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(120, 100, 80)).save(buffer, format=fmt)
    return buffer.getvalue()


def test_normalises_to_jpeg():
    data, content_type = normalize_uploaded_image_bytes(
        _image_bytes(400, 500, "PNG"), "image/png", "outfit.png", max_upload_mb=5
    )
    assert content_type == "image/jpeg"
    assert data[:2] == b"\xff\xd8"  # JPEG magic bytes


def test_downscales_large_dimensions():
    data, _ = normalize_uploaded_image_bytes(
        _image_bytes(4000, 3000), "image/jpeg", "big.jpg", max_upload_mb=5
    )
    with Image.open(BytesIO(data)) as image:
        assert max(image.size) <= 1600


def test_small_image_dimensions_are_preserved():
    data, _ = normalize_uploaded_image_bytes(
        _image_bytes(300, 200), "image/jpeg", "small.jpg", max_upload_mb=5
    )
    with Image.open(BytesIO(data)) as image:
        assert image.size == (300, 200)


def test_content_type_falls_back_to_file_extension():
    """iOS sends application/octet-stream for camera uploads."""
    data, content_type = normalize_uploaded_image_bytes(
        _image_bytes(200, 200), "application/octet-stream", "photo.HEIC", max_upload_mb=5
    )
    assert content_type == "image/jpeg"
    assert data


def test_rejects_unsupported_extension():
    with pytest.raises(UnsupportedImageFormatError):
        normalize_uploaded_image_bytes(b"abc", "application/pdf", "doc.pdf", max_upload_mb=5)


def test_rejects_undecodable_bytes():
    with pytest.raises(UnsupportedImageFormatError):
        normalize_uploaded_image_bytes(b"nonsense", "image/jpeg", "fake.jpg", max_upload_mb=5)


def test_raises_when_image_cannot_be_compressed_under_limit():
    with pytest.raises(ImageTooLargeError):
        normalize_uploaded_image_bytes(
            _image_bytes(2000, 2000), "image/jpeg", "big.jpg", max_upload_mb=0
        )


def test_decoded_pixel_limit_is_enforced_before_conversion(monkeypatch):
    # Lower the budget to exercise the guard without allocating a giant image.
    monkeypatch.setattr("app.image_processing.MAX_IMAGE_PIXELS", 10_000)
    with pytest.raises(ImageTooLargeError):
        normalize_uploaded_image_bytes(
            _image_bytes(101, 100), "image/jpeg", "outfit.jpg", max_upload_mb=5,
        )


def test_disallowed_actual_format_cannot_hide_behind_jpeg_mime_type():
    with pytest.raises(UnsupportedImageFormatError):
        normalize_uploaded_image_bytes(
            _image_bytes(100, 100, "GIF"), "image/jpeg", "outfit.jpg", max_upload_mb=5,
        )
