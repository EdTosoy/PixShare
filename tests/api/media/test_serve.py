from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.helpers.posts import create_test_image


@pytest.mark.asyncio
async def test_serve_uploaded_file(
    client: AsyncClient,
):
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    filename = "test-image.jpg"
    file_path = upload_dir / filename
    file_content = b"fake image content"

    _ = file_path.write_bytes(file_content)

    response = await client.get(f"/uploads/{filename}")

    assert response.status_code == 200
    assert response.content == file_content


@pytest.mark.asyncio
async def test_serve_uploaded_file_returns_404_when_not_found(
    client: AsyncClient,
):
    response = await client.get("/uploads/does-not-exist.jpg")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_serve_uploaded_file_returns_content_type(
    client: AsyncClient,
):
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    filename = "content-type-test.jpg"
    file_path = upload_dir / filename
    _ = file_path.write_bytes(create_test_image())

    response = await client.get(f"/uploads/{filename}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
