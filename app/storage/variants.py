"""Bounded, atomic, optional derivatives; originals are never rewritten."""

import shutil
import tempfile
import warnings
from pathlib import Path
from typing import cast

from PIL import Image, ImageOps

from app.core.images import IMAGE_WORK_LOCK, check_dimensions
from app.schemas.media import ImageInfo, ImageVariant

VARIANT_EDGES = (320, 640, 1280, 1920)
VARIANT_VERSION = "v1"


def generate_variants(original: Path, group: Path, url_prefix: str) -> ImageInfo:
    with IMAGE_WORK_LOCK, warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(original) as source:
            check_dimensions(source)
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Unsupported image")
            if getattr(source, "is_animated", False):
                raise ValueError("Keep animated originals animated")
            # Transpose before resizing; omit EXIF/GPS from derivatives.
            image = ImageOps.exif_transpose(source)
        try:
            profile = cast(bytes, image.info.get("icc_profile", b""))
            if profile and image.mode not in {"RGB", "RGBA"}:
                # Do not attach a gray/CMYK profile to converted RGB pixels.
                # Keep the color-managed original unless conversion is available.
                raise ValueError("Profiled non-RGB images retain original delivery")
            if image.mode not in {"RGB", "RGBA"}:
                converted = image.convert(
                    "RGBA" if "transparency" in image.info or image.mode == "LA" else "RGB"
                )
                image.close()
                image = converted
            group.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".variant-", dir=group.parent))
            try:
                variants: list[ImageVariant] = []
                longest = max(image.size)
                for requested in VARIANT_EDGES:
                    edge = min(requested, longest)
                    name = f"{VARIANT_VERSION}-{edge}.webp"
                    with ImageOps.contain(
                        image, (edge, edge), Image.Resampling.LANCZOS
                    ) as resized:
                        resized.save(temporary / name, "WEBP", quality=80, method=4, icc_profile=profile)
                        variants.append(
                            ImageVariant(
                                url=f"{url_prefix}/{name}",
                                width=resized.width,
                                height=resized.height,
                            )
                        )
                    if edge == longest:
                        break
                info = ImageInfo(width=image.width, height=image.height, variants=variants)
                _ = (temporary / "manifest.json").write_text(info.model_dump_json())
                # A complete manifest and all variants become visible together.
                if group.exists():
                    shutil.rmtree(group)
                _ = temporary.rename(group)
                return info
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        finally:
            image.close()
