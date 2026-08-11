from pathlib import Path
from typing import BinaryIO, final, override
from uuid import uuid4

from app.storage.base import Storage


@final
class LocalStorage(Storage):
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)

    @override
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
    ) -> str:
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        extension = Path(filename).suffix
        stored_filename = f"{uuid4()}{extension}"
        destination = self.upload_dir / stored_filename

        _ = destination.write_bytes(file.read())

        return f"/uploads/{stored_filename}"

    @override
    async def delete(self, url: str) -> None:
        filename = Path(url).name
        destination = self.upload_dir / filename

        if destination.exists():
            destination.unlink()
