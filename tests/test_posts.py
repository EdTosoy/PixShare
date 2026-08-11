from io import BytesIO
from typing import TypedDict, cast

import pytest
from httpx import AsyncClient
from PIL import Image

from app.models.post import Post
from app.models.user import User
from app.storage.local import LocalStorage
from tests.conftest import session_factory


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
    assert updated_post["updated_at"] != post["updated_at"]


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
async def test_update_post_not_authorized(
    client: AsyncClient,
    other_user: User,
):
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

    response = await client.patch(
        f"/posts/{post.id}",
        json={"caption": "Updated caption"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to update this post"
    )


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
