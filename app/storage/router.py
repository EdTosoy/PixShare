from typing import BinaryIO, final, override

from app.core.config import Settings
from app.schemas.media import ImageInfo
from app.storage.base import Storage, StorageUnavailable
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


@final
class MediaStorage(Storage):
    """Select new writes independently of the location of older records."""

    def __init__(self, settings: Settings):
        self.local = LocalStorage(settings.uploads_dir)
        self.s3 = S3Storage(settings) if settings.s3_bucket else None
        self.provider = settings.storage_provider

    def backend(self, reference: str) -> Storage:
        if reference.startswith("s3://"):
            if self.s3 is None:
                raise StorageUnavailable("Object storage configuration is required for this record")
            return self.s3
        return self.local

    @override
    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        backend = self.s3 if self.provider == "s3" else self.local
        if backend is None:
            raise StorageUnavailable("Object storage is unavailable")
        return await backend.upload(file, filename, content_type)

    @override
    async def delete(self, url: str) -> None:
        await self.backend(url).delete(url)

    @override
    async def describe(self, url: str) -> ImageInfo | None:
        return await self.backend(url).describe(url)

    @override
    def public_url(self, reference: str) -> str:
        return self.backend(reference).public_url(reference)
