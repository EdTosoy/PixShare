from abc import ABC, abstractmethod
from typing import BinaryIO

from app.schemas.media import ImageInfo


class Storage(ABC):
    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload and return a durable reference (local URL or owned s3:// key)."""

    @abstractmethod
    async def delete(self, url: str) -> None:
        """Delete an original and its variants by their durable reference."""

    async def describe(self, url: str) -> ImageInfo | None:  # pyright: ignore[reportUnusedParameter]
        """Optional responsive derivatives; legacy/unsupported objects return None."""
        return None

    def public_url(self, reference: str) -> str:
        """Resolve a durable reference at response time; never return signed URLs."""
        return reference


class StorageUnavailable(Exception):
    """Safe API error; never attach SDK messages, request details, or credentials."""
