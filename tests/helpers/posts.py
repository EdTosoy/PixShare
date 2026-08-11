from io import BytesIO
from typing import TypedDict, cast

import pytest
from httpx import AsyncClient
from PIL import Image


class PostData(TypedDict):
    id: str
    caption: str | None
    url: str
    file_name: str
    file_type: str
    created_at: str
    updated_at: str


def create_test_image() -> bytes:
    image = Image.new("RGB", (1, 1), "white")

    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    return buffer.getvalue()


async def create_test_post(client: AsyncClient) -> PostData:
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

    return cast(PostData, response.json())


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
