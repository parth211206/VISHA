"""Snake image inference API with binary and optional taxonomy predictions.

The taxonomy predictions are experimental model outputs, not a clinical diagnosis
or a basis for selecting or dosing antivenom.
"""
from __future__ import annotations

import io
import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from app.services.ml_service import MLModelService, ModelUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml-inference", tags=["ml-inference"])
ml_service = MLModelService()

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


@router.get("/status")
async def inference_status() -> dict[str, Any]:
    """Check binary and taxonomy model configuration without forcing model loading."""
    return ml_service.status()


@router.post("/predict")
async def predict_snake_venomous(file: UploadFile = File(...)) -> dict[str, Any]:
    """Return binary scores and taxonomy candidates when a trained taxonomy model is available."""
    try:
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large. Maximum upload size is 12 MiB.",
        )

    try:
        # Verify actual content rather than trusting file name or MIME type.
        with Image.open(io.BytesIO(contents)) as probe:
            image_format = (probe.format or "").upper()
            width, height = probe.size
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Supported image formats are JPEG, PNG, and WEBP.",
                )
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image dimensions are invalid or exceed the 20-megapixel limit.",
                )
            probe.verify()

        with Image.open(io.BytesIO(contents)) as decoded:
            image = decoded.convert("RGB")
            image.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The upload is not a valid supported image. Try a JPEG, PNG, or WEBP file.",
        ) from exc

    try:
        return await run_in_threadpool(ml_service.predict, image)
    except ModelUnavailableError as exc:
        logger.warning("Image inference requested but the binary model is unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Image inference request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image inference failed. Check the backend terminal for details.",
        ) from exc
