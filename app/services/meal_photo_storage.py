"""Save meal images to disk: full-size JPEG + thumbnail for UI."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Tuple

from app.core.config import MEAL_PHOTOS_DIR

logger = logging.getLogger(__name__)

_MAX_BYTES = 15 * 1024 * 1024
_THUMB_MAX = 480


def try_save_meal_photos(user_id: int, meal_id: int, image_bytes: bytes) -> tuple[str | None, str | None]:
    """
    Write full.jpg and thumb.jpg under MEAL_PHOTOS_DIR / {user_id} / {meal_id} /.
    Returns (relative_path_large, relative_path_thumb) using forward slashes, or (None, None) on failure.
    """
    if not image_bytes or len(image_bytes) > _MAX_BYTES:
        return None, None

    rel_base = f"{user_id}/{meal_id}"
    dest_dir = MEAL_PHOTOS_DIR / rel_base
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("meal photos mkdir failed: %s", e)
        return None, None

    large_name = "full.jpg"
    thumb_name = "thumb.jpg"
    large_path = dest_dir / large_name
    thumb_path = dest_dir / thumb_name

    try:
        from PIL import Image

        im = Image.open(io.BytesIO(image_bytes))
        im = im.convert("RGB")
        im.save(large_path, "JPEG", quality=88, optimize=True)
        thumb = im.copy()
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        thumb.thumbnail((_THUMB_MAX, _THUMB_MAX), resample)
        thumb.save(thumb_path, "JPEG", quality=82, optimize=True)
    except Exception as e:
        logger.warning("PIL meal photo save failed, fallback copy: %s", e)
        try:
            large_path.write_bytes(image_bytes)
            thumb_path.write_bytes(image_bytes)
        except OSError as e2:
            logger.warning("meal photo raw write failed: %s", e2)
            return None, None

    rel_large = f"{rel_base}/{large_name}".replace("\\", "/")
    rel_thumb = f"{rel_base}/{thumb_name}".replace("\\", "/")
    return rel_large, rel_thumb
