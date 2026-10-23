"""Shared decode budget for validation and derivative generation."""

import threading

from PIL import Image

# A compressed 10 MiB file can otherwise expand to hundreds of megapixels.
MAX_SOURCE_PIXELS = 16_000_000
MAX_SOURCE_EDGE = 20_000
IMAGE_WORK_LOCK = threading.Lock()


class ImageDimensionsError(ValueError):
    pass


def check_dimensions(image: Image.Image) -> None:
    width, height = image.size
    if (
        width * height > MAX_SOURCE_PIXELS
        or max(width, height) > MAX_SOURCE_EDGE
        or min(width, height) < 1
    ):
        raise ImageDimensionsError("Image dimensions exceed the decode budget")
