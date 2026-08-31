"""Image upload endpoint (for manually added inventory cards).

Accepts a base64-encoded file in a JSON body to avoid a multipart dependency.
"""
from __future__ import annotations

import base64
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/images", tags=["images"])

_ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}


class ImageUploadIn(BaseModel):
    filename: str
    data: str


@router.post("/upload")
def upload_image(payload: ImageUploadIn) -> dict:
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in _ALLOWED:
        raise HTTPException(status_code=422, detail="Formato de imagen no soportado")

    try:
        content = base64.b64decode(payload.data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Imagen no válida") from exc
    if not content:
        raise HTTPException(status_code=422, detail="Imagen vacía")

    settings = get_settings()
    target_dir = settings.images_dir / "manual"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    (target_dir / filename).write_bytes(content)

    return {"image_path": f"manual/{filename}"}
