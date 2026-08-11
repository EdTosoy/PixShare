from io import BytesIO
from pathlib import Path

import pytest

from app.storage.local import LocalStorage


@pytest.mark.asyncio
async def test_upload_creates_file(tmp_path: Path):
    storage = LocalStorage(upload_dir=str(tmp_path))

    content = b"hello world"

    url = await storage.upload(
        file=BytesIO(content),
        filename="test.txt",
        content_type="text/plain",
    )

    file_path = tmp_path / Path(url).name

    assert file_path.exists()
    assert file_path.read_bytes() == content


@pytest.mark.asyncio
async def test_upload_returns_url(tmp_path: Path):
    storage = LocalStorage(upload_dir=str(tmp_path))

    url = await storage.upload(
        file=BytesIO(b"hello"),
        filename="photo.jpg",
        content_type="image/jpeg",
    )

    assert url.startswith("/uploads/")
    assert url.endswith(".jpg")


@pytest.mark.asyncio
async def test_upload_generates_unique_filename(tmp_path: Path):
    storage = LocalStorage(upload_dir=str(tmp_path))

    first_url = await storage.upload(
        file=BytesIO(b"first"),
        filename="photo.jpg",
        content_type="image/jpeg",
    )

    second_url = await storage.upload(
        file=BytesIO(b"second"),
        filename="photo.jpg",
        content_type="image/jpeg",
    )

    assert first_url != second_url
    assert len(list(tmp_path.iterdir())) == 2


@pytest.mark.asyncio
async def test_delete_removes_file(tmp_path: Path):
    storage = LocalStorage(upload_dir=str(tmp_path))

    url = await storage.upload(
        file=BytesIO(b"hello"),
        filename="test.txt",
        content_type="text/plain",
    )

    file_path = tmp_path / Path(url).name

    assert file_path.exists()

    await storage.delete(url)

    assert not file_path.exists()


@pytest.mark.asyncio
async def test_delete_nonexistent_file_does_not_fail(tmp_path: Path):
    storage = LocalStorage(upload_dir=str(tmp_path))

    await storage.delete("/uploads/does-not-exist.txt")
