from typing import cast

import pytest
from httpx import AsyncClient

from app.models.post import Post
from app.models.user import User
from app.storage.local import LocalStorage
from tests.conftest import session_factory
from tests.helpers.posts import PostData, create_test_post


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


@pytest.mark.asyncio
async def test_delete_post_not_authorized(client: AsyncClient, other_user: User):
    async with session_factory() as session:
        post = Post(
            user_id=other_user.id,
            url="https://example.com/image.jpg",
            file_name="image.jpg",
            file_type="image/jpeg",
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)

    response = await client.delete(f"/posts/{post.id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to delete this post"


@pytest.mark.asyncio
async def test_delete_post_removes_file(client: AsyncClient):
    post = await create_test_post(client)

    storage = LocalStorage()
    file_path = storage.upload_dir / post["url"].split("/")[-1]

    assert file_path.exists()

    response = await client.delete(f"/posts/{post['id']}")

    assert response.status_code == 200
    assert not file_path.exists()
