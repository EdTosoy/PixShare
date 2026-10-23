import asyncio
import warnings
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.images import IMAGE_WORK_LOCK, ImageDimensionsError, check_dimensions

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_image(content: bytes, expected_format: str) -> None:
    # Decode off the event loop, one image at a time per API process.
    with IMAGE_WORK_LOCK, warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(content)) as image:
            check_dimensions(image)
            if image.format != expected_format:
                raise ValueError("Image format does not match its MIME type")
            image.verify()
        with Image.open(BytesIO(content)) as image:
            check_dimensions(image)
            _ = image.load()


async def validate_upload(file: UploadFile) -> None:
    content_type = file.content_type

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large",
        )

    try:
        await asyncio.to_thread(validate_image, content, ALLOWED_IMAGE_TYPES[content_type])
    except ImageDimensionsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image dimensions are too large. Use at most 16 megapixels and 20,000 pixels per side.",
        )
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        )

    await file.seek(0)
