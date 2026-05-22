from __future__ import annotations

import os
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image

MEDIA_URL_PREFIX = "/media/additives"

_MAX_BYTES = 15 * 1024 * 1024


def get_upload_root() -> Path:
    """
    Root directory on disk for additive photo files.

    Railway: env ADDITIVE_PHOTO_UPLOAD_DIR=/app/data/uploads/additives
    Local default: see app.core.config.ADDITIVE_PHOTO_UPLOAD_DIR
    """
    env_val = os.getenv("ADDITIVE_PHOTO_UPLOAD_DIR")
    if env_val:
        return Path(env_val)
    from app.core.config import ADDITIVE_PHOTO_UPLOAD_DIR

    return ADDITIVE_PHOTO_UPLOAD_DIR


def save_additive_photo_pair(
    image_bytes: bytes,
    *,
    user_id: int,
    thumb_size: tuple[int, int] = (320, 320),
) -> dict[str, str]:
    """
    Save large JPEG and thumbnail. Returns DB web paths:

    /media/additives/<user_id>/original/<uuid>.jpg
    /media/additives/<user_id>/thumbs/<uuid>_thumb.jpg
    """
    if not image_bytes or len(image_bytes) > _MAX_BYTES:
        raise ValueError("image_bytes missing or too large")

    upload_root = get_upload_root()
    original_dir = upload_root / str(user_id) / "original"
    thumb_dir = upload_root / str(user_id) / "thumbs"
    original_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    original_filename = f"{file_id}.jpg"
    thumb_filename = f"{file_id}_thumb.jpg"
    original_path = original_dir / original_filename
    thumb_path = thumb_dir / thumb_filename

    with Image.open(BytesIO(image_bytes)) as img:
        img = img.convert("RGB")

        large = img.copy()
        large.thumbnail((1600, 1600))
        large.save(original_path, format="JPEG", quality=88, optimize=True)

        thumb = img.copy()
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        thumb.thumbnail(thumb_size, resample)
        thumb.save(thumb_path, format="JPEG", quality=78, optimize=True)

    return {
        "photo_large": f"{MEDIA_URL_PREFIX}/{user_id}/original/{original_filename}",
        "photo_thumb": f"{MEDIA_URL_PREFIX}/{user_id}/thumbs/{thumb_filename}",
    }
