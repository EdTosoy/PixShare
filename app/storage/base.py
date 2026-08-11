from abc import ABC, abstractmethod
from typing import BinaryIO


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
