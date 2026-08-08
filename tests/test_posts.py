from typing import TypedDict, cast
from uuid import UUID

import pytest
from httpx import AsyncClient


class PostData(TypedDict):
    id: str
    caption: str | None
    url: str
    file_name: str
    file_type: str
    created_at: str
    updated_at: str


async def create_test_post(client: AsyncClient) -> PostData:
    response = await client.post(
        "/posts",
        json={
            "caption": "Test post",
            "url": "https://example.com/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image/jpeg",
        },
    )

    assert response.status_code == 201

    return cast(PostData, response.json())


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient):
    post = await create_test_post(client)

    assert post["caption"] == "Test post"
    assert post["url"] == "https://example.com/image.jpg"
    assert post["file_name"] == "image.jpg"
    assert post["file_type"] == "image/jpeg"
    assert UUID(post["id"])


@pytest.mark.asyncio
async def test_get_posts(client: AsyncClient):
    _ = await create_test_post(client)

    response = await client.get("/posts")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert len(posts) == 1
    assert posts[0]["caption"] == "Test post"


@pytest.mark.asyncio
async def test_get_post_by_id(client: AsyncClient):
    post = await create_test_post(client)

    response = await client.get(f"/posts/{post['id']}")

    assert response.status_code == 200

    returned_post = cast(PostData, response.json())

    assert returned_post["id"] == post["id"]


@pytest.mark.asyncio
async def test_get_post_by_id_not_found(client: AsyncClient):
    post_id = "00000000-0000-0000-0000-000000000000"

    response = await client.get(f"/posts/{post_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"


@pytest.mark.asyncio
async def test_update_post(client: AsyncClient):
    post = await create_test_post(client)

    response = await client.patch(
        f"/posts/{post['id']}",
        json={
            "caption": "Updated caption",
        },
    )

    assert response.status_code == 200

    updated_post = cast(PostData, response.json())

    assert updated_post["id"] == post["id"]
    assert updated_post["caption"] == "Updated caption"
    assert updated_post["url"] == post["url"]
    assert updated_post["file_name"] == post["file_name"]
    assert updated_post["file_type"] == post["file_type"]


@pytest.mark.asyncio
async def test_update_post_not_found(client: AsyncClient):
    post_id = "00000000-0000-0000-0000-000000000000"

    response = await client.patch(
        f"/posts/{post_id}",
        json={
            "caption": "Updated caption",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"


@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient):
    post = await create_test_post(client)

    response = await client.delete(f"/posts/{post['id']}")

    assert response.status_code == 200

    deleted_post = cast(PostData, response.json())

    assert deleted_post["id"] == post["id"]

    get_response = await client.get(f"/posts/{post['id']}")

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_not_found(client: AsyncClient):
    post_id = "00000000-0000-0000-0000-000000000000"

    response = await client.delete(f"/posts/{post_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"
