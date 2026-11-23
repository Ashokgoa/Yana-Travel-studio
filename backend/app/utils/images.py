"""Image validation and normalisation for uploads (PRD 12.1).

- The real format is detected from the file content (not the extension).
- Decompression-bomb protection via a pixel limit.
- EXIF orientation is applied, then all metadata (incl. GPS location) is dropped
  by re-encoding.
- Large images are downscaled; a small thumbnail is produced for lists/galleries.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 60_000_000  # ~60 MP; larger raises DecompressionBombError

ALLOWED_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}
MAX_EDGE = 2400  # px, long edge of the stored image (sharp enough for A4 brochure pages)
THUMB_EDGE = 480


class ImageError(ValueError):
    """Upload is not an acceptable image; message is shown to the user."""


@dataclass
class ProcessedImage:
    data: bytes
    extension: str
    mime_type: str
    width: int
    height: int
    thumbnail: bytes


def process_image(raw: bytes, max_bytes: int) -> ProcessedImage:
    if not raw:
        raise ImageError("The file is empty.")
    if len(raw) > max_bytes:
        raise ImageError(f"The file is too large ({len(raw) / 1_048_576:.1f} MB). Maximum is {max_bytes // 1_048_576} MB.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            probe.verify()  # structural check
        if fmt not in ALLOWED_FORMATS:
            raise ImageError("Unsupported image type. Use JPG, PNG or WEBP.")
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Image.DecompressionBombError:
        raise ImageError("The image has too many pixels to process safely.")
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ImageError("The file is not a valid image (it may be corrupted or not really a JPG/PNG/WEBP).")

    img = ImageOps.exif_transpose(img)  # respect camera orientation, then metadata is discarded on save
    ext, mime = ALLOWED_FORMATS[fmt]
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    if fmt == "JPEG":
        img.save(out, "JPEG", quality=85, optimize=True, progressive=True)
    elif fmt == "PNG":
        img.save(out, "PNG", optimize=True)
    else:
        img.save(out, "WEBP", quality=85, method=4)

    thumb = img.copy()
    thumb.thumbnail((THUMB_EDGE, THUMB_EDGE), Image.Resampling.LANCZOS)
    if thumb.mode not in ("RGB", "L"):
        background = Image.new("RGB", thumb.size, (255, 255, 255))
        background.paste(thumb, mask=thumb.convert("RGBA").split()[-1])
        thumb = background
    tout = io.BytesIO()
    thumb.save(tout, "JPEG", quality=80, optimize=True)

    return ProcessedImage(out.getvalue(), ext, mime, img.width, img.height, tout.getvalue())
