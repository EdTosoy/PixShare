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
