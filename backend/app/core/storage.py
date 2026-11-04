"""Shared local-file storage locations for uploaded EventHub media."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_ROOT = Path(
    os.getenv("EVENT_UPLOAD_DIR", str(DEFAULT_UPLOAD_ROOT))
).expanduser().resolve()
EVENT_COVER_IMAGE_DIR = UPLOAD_ROOT / "event-covers"
EVENT_COVER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def resolve_event_cover_path(image_url: str | None) -> Path | None:
    """Resolve only generated event-cover URLs to files inside the upload directory."""
    if not image_url or not image_url.startswith("/uploads/event-covers/"):
        return None
    filename = image_url.removeprefix("/uploads/event-covers/")
    if (
        not filename
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or Path(filename).name != filename
    ):
        return None
    candidate = (EVENT_COVER_IMAGE_DIR / filename).resolve()
    if candidate.parent != EVENT_COVER_IMAGE_DIR.resolve():
        return None
    return candidate
