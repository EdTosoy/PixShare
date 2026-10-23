from typing import cast

import pytest
from httpx import AsyncClient

from tests.helpers.posts import PostData, create_test_image


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient):
    response = await client.post(
        "/posts",
        data={
            "caption": "Test post",
        },
        files={
            "file": (
                "image.jpg",
                create_test_image(),
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 201

    post = cast(PostData, response.json())

    assert post["caption"] == "Test post"
    assert post["file_name"] == "image.jpg"
    assert post["file_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_create_post_rejects_unsupported_file_type(
    client: AsyncClient,
):
    response = await client.post(
        "/posts",
        files={
            "file": (
                "test.txt",
                b"not an image",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"


@pytest.mark.asyncio
async def test_create_post_rejects_oversized_file(
    client: AsyncClient,
):
    oversized_file = b"x" * (10 * 1024 * 1024 + 1)

    response = await client.post(
        "/posts",
        files={
            "file": (
                "large.jpg",
                oversized_file,
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File too large"


@pytest.mark.asyncio
async def test_create_post_rejects_invalid_image(
    client: AsyncClient,
):
    response = await client.post(
        "/posts",
        files={
            "file": (
                "fake.jpg",
                b"this is not actually a jpeg",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid image file"


@pytest.mark.asyncio
async def test_rejects_image_mime_mismatch(client: AsyncClient):
    response = await client.post(
        "/posts", files={"file": ("fake.png", create_test_image(), "image/png")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid image file"


@pytest.mark.asyncio
@pytest.mark.parametrize("pixel_limit", [20, 60])
async def test_rejects_decompression_bomb(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, pixel_limit: int
):
    from io import BytesIO

    from PIL import Image

    # Cross both Pillow warning and error thresholds without huge allocations.
    image = Image.new("RGB", (10, 10), "white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", pixel_limit)
    response = await client.post(
        "/posts", files={"file": ("large.jpg", buffer.getvalue(), "image/jpeg")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid image file"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "format_name,mime,extension",
    [
        ("JPEG", "image/jpeg", ".jpg"),
        ("PNG", "image/png", ".png"),
        ("WEBP", "image/webp", ".webp"),
    ],
)
async def test_supported_formats_use_verified_extensions(
    client: AsyncClient, format_name: str, mime: str, extension: str
):
    from io import BytesIO

    from PIL import Image

    image = Image.new("RGB", (8, 8), "blue")
    buffer = BytesIO()
    image.save(buffer, format=format_name)
    response = await client.post(
        "/posts", files={"file": ("misleading.html", buffer.getvalue(), mime)}
    )
    assert response.status_code == 201
    post = cast(PostData, response.json())
    assert post["url"].endswith(extension)
    assert post["file_type"] == mime
