"""Image validation and re-encoding for uploads.

Every uploaded image is decoded and re-encoded with Pillow before it is stored. That
  * strips EXIF metadata (phone photos often carry GPS coordinates),
  * applies the EXIF rotation so photos are not sideways,
  * caps the dimensions so pages load fast,
  * guarantees we only ever serve real JPEG/PNG files (no SVG/HTML disguised as images).
"""
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, ImageOps

# Refuse "decompression bombs": images that are tiny on disk but huge once decoded.
Image.MAX_IMAGE_PIXELS = 40_000_000

MAX_UPLOAD_MB = 8
MAX_PHOTO_SIDE = 1600
# Phone screenshots are tall (e.g. 1080x2400); keep them near full size so the QR stays scannable.
MAX_QR_SIDE = 2400


def validate_upload_size(file):
    if file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f"Image is too large. Please upload a file under {MAX_UPLOAD_MB} MB.")


def _load(uploaded):
    uploaded.seek(0)
    img = Image.open(uploaded)
    img.load()
    return ImageOps.exif_transpose(img)


def _flatten_to_rgb(img):
    """Return an RGB image; transparent areas become white."""
    if img.mode == "P" and "transparency" in img.info:
        img = img.convert("RGBA")
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.getchannel("A"))
        return background
    return img.convert("RGB")


def process_photo(uploaded):
    """Face photo -> JPEG bytes, max 1600px on the longest side."""
    img = _flatten_to_rgb(_load(uploaded))
    img.thumbnail((MAX_PHOTO_SIDE, MAX_PHOTO_SIDE), Image.LANCZOS)
    out = BytesIO()
    img.save(out, "JPEG", quality=88, optimize=True)
    return out.getvalue()


def process_qr(uploaded):
    """QR screenshot -> PNG bytes (lossless, so the code stays crisp and scannable)."""
    img = _flatten_to_rgb(_load(uploaded))
    img.thumbnail((MAX_QR_SIDE, MAX_QR_SIDE), Image.LANCZOS)
    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()
