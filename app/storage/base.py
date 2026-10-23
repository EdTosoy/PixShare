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
        """Upload a file and return its URL."""

    @abstractmethod
    async def delete(self, url: str) -> None:
        """Delete a file by its URL."""

    async def describe(self, url: str) -> ImageInfo | None:  # pyright: ignore[reportUnusedParameter]
        """Optional responsive derivatives; legacy/unsupported objects return None."""
        return None
