"""Shared file-type detection utilities.

Used by agent classes to route file bytes into the correct processing path
(image → base64 vision, PDF → text extraction).
"""

from __future__ import annotations

_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}
)

_MEDIA_TYPE_MAP: dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


def guess_media_type(filename: str) -> str:
    """Guess MIME type from file extension.  Defaults to image/jpeg."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MEDIA_TYPE_MAP.get(ext, "image/jpeg")


def is_image(filename: str) -> bool:
    """True if filename extension is a recognised image format."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in _IMAGE_EXTENSIONS


def is_pdf(filename: str) -> bool:
    """True if filename extension is 'pdf'."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext == "pdf"
