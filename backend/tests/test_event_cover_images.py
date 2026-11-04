from io import BytesIO

import pytest
from PIL import Image

from app.core.image_validation import ALLOWED_IMAGE_FORMATS, inspect_cover_image
from app.core.storage import resolve_event_cover_path


def make_image(image_format: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 36), color="white").save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_accepts_supported_image_formats(image_format):
    detected, width, height = inspect_cover_image(make_image(image_format))
    assert detected == image_format
    assert (width, height) == (64, 36)
    assert detected in ALLOWED_IMAGE_FORMATS


def test_rejects_non_image_bytes():
    with pytest.raises(ValueError, match="not a valid image"):
        inspect_cover_image(b"not an image")


def test_rejects_empty_upload():
    with pytest.raises(ValueError, match="select an image"):
        inspect_cover_image(b"")


def test_rejects_unsupported_image_format():
    with pytest.raises(ValueError, match="Only JPG, PNG, and WebP"):
        inspect_cover_image(make_image("GIF"))


def test_cover_path_rejects_untrusted_paths():
    assert resolve_event_cover_path("/uploads/event-covers/../../.env") is None
    assert resolve_event_cover_path("https://example.com/image.jpg") is None


def test_cover_path_rejects_windows_separators():
    assert resolve_event_cover_path(
        "/uploads/event-covers/..\\..\\.env"
    ) is None
