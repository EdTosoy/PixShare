import asyncio
import logging
import re
import shutil
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO, final, override
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.media import ImageInfo
from app.storage.base import Storage
from app.storage.variants import generate_variants

logger = logging.getLogger(__name__)


def local_filename(url: str) -> str | None:
    if not url.startswith("/uploads/"):
        return None
    filename = url.removeprefix("/uploads/")
    if not filename or filename in {".", "..", "_variants"} or "/" in filename or "\\" in filename:
        return None
    return filename


@final
class LocalStorage(Storage):
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)

    @override
    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        extension = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }.get(content_type, Path(filename).suffix.lower())
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", extension):
            extension = ""
        stored_filename = f"{uuid4()}{extension}"
        destination = self.upload_dir / stored_filename

        def write() -> None:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            created = False
            try:
                with destination.open("xb") as output:
                    created = True
                    shutil.copyfileobj(file, output)
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise

        await asyncio.to_thread(write)
        url = f"/uploads/{stored_filename}"
        if content_type in {"image/jpeg", "image/png", "image/webp"}:
            _ = await self.ensure_variants(url)
        return url

    def read_info(self, filename: str) -> ImageInfo | None:
        group = self.upload_dir / "_variants" / filename
        try:
            if (
                not (self.upload_dir / filename).is_file()
                or group.is_symlink()
                or group.parent.is_symlink()
            ):
                return None
            info = ImageInfo.model_validate_json((group / "manifest.json").read_bytes())
            prefix = f"/uploads/_variants/{filename}/"
            if not info.variants:
                return None
            for variant in info.variants:
                name = variant.url.removeprefix(prefix)
                if (
                    not variant.url.startswith(prefix)
                    or not re.fullmatch(r"v1-\d+\.webp", name)
                    or not (group / name).is_file()
                ):
                    return None
            return info
        except (OSError, ValueError, ValidationError):
            return None

    @override
    async def describe(self, url: str) -> ImageInfo | None:
        filename = local_filename(url)
        return await asyncio.to_thread(self.read_info, filename) if filename else None

    async def ensure_variants(self, url: str) -> ImageInfo | None:
        filename = local_filename(url)
        if filename is None:
            return None
        info = await self.describe(url)
        if info is not None:
            return info
        try:
            if (self.upload_dir / "_variants").is_symlink():
                return None
            return await asyncio.to_thread(
                generate_variants,
                self.upload_dir / filename,
                self.upload_dir / "_variants" / filename,
                f"/uploads/_variants/{filename}",
            )
        except Exception:  # noqa: BLE001 - optional derivatives must preserve originals
            logger.warning("Image variants unavailable; original retained")
            return None

    @override
    async def delete(self, url: str) -> None:
        filename = local_filename(url)
        if filename is None:
            return

        def remove() -> None:
            error: OSError | None = None
            try:
                (self.upload_dir / filename).unlink(missing_ok=True)
            except OSError as exc:
                error = exc
            # Still attempt every associated object if original removal fails.
            group = self.upload_dir / "_variants" / filename
            try:
                if group.parent.is_symlink():
                    pass
                elif group.is_symlink():
                    group.unlink()
                elif group.exists():
                    shutil.rmtree(group)
                with suppress(OSError):
                    group.parent.rmdir()
            except OSError as exc:
                error = error or exc
            if error:
                raise error

        await asyncio.to_thread(remove)
