from typing import cast

import pytest
from httpx import AsyncClient

from tests.helpers.posts import PostData, create_test_post


@pytest.mark.asyncio
async def test_get_posts(client: AsyncClient):
    _ = await create_test_post(client)

    response = await client.get("/posts")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert len(posts) == 1
    assert posts[0]["caption"] == "Test post"


@pytest.mark.asyncio
async def test_get_posts_with_pagination(client: AsyncClient):
    first = await create_test_post(client)
    second = await create_test_post(client)
    _third = await create_test_post(client)

    response = await client.get("/posts?limit=2&offset=1")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert len(posts) == 2
    assert posts[0]["id"] == second["id"]
    assert posts[1]["id"] == first["id"]


@pytest.mark.asyncio
async def test_get_posts_invalid_limit(client: AsyncClient):
    response = await client.get("/posts?limit=101")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_posts_invalid_offset(client: AsyncClient):
    response = await client.get("/posts?offset=-1")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_posts_filter_by_file_type(client: AsyncClient):
    _ = await create_test_post(client)

    response = await client.get("/posts?file_type=image/jpeg")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert len(posts) == 1
    assert posts[0]["file_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_get_posts_filter_by_file_type_no_match(client: AsyncClient):
    _ = await create_test_post(client)

    response = await client.get("/posts?file_type=image/png")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert len(posts) == 0


@pytest.mark.asyncio
async def test_get_posts_sort_oldest(client: AsyncClient):
    first = await create_test_post(client)
    second = await create_test_post(client)

    response = await client.get("/posts?sort=oldest")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert posts[0]["id"] == first["id"]
    assert posts[1]["id"] == second["id"]


@pytest.mark.asyncio
async def test_get_posts_sort_newest(client: AsyncClient):
    first = await create_test_post(client)
    second = await create_test_post(client)

    response = await client.get("/posts?sort=newest")

    assert response.status_code == 200

    posts = cast(list[PostData], response.json())

    assert posts[0]["id"] == second["id"]
    assert posts[1]["id"] == first["id"]


@pytest.mark.asyncio
async def test_get_posts_invalid_sort(client: AsyncClient):
    response = await client.get("/posts?sort=random")

    assert response.status_code == 422


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
