"""Validation helpers for organizer-uploaded event cover images."""
from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_COVER_IMAGE_BYTES = 5 * 1024 * 1024
MAX_COVER_IMAGE_PIXELS = 40_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def inspect_cover_image(content: bytes) -> tuple[str, int, int]:
    """Validate image bytes and return the detected format and dimensions."""
    if not content:
        raise ValueError("Please select an image file")
    if len(content) > MAX_COVER_IMAGE_BYTES:
        raise ValueError("Cover images must be 5 MB or smaller")
    try:
        with Image.open(BytesIO(content)) as inspected:
            image_format = inspected.format
            width, height = inspected.size
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError("Only JPG, PNG, and WebP images are supported")
            if (
                width < 1
                or height < 1
                or width * height > MAX_COVER_IMAGE_PIXELS
            ):
                raise ValueError("Image dimensions are too large")
            inspected.verify()
            return image_format, width, height
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("The uploaded file is not a valid image") from error
