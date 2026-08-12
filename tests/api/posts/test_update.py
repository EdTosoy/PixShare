from pathlib import Path
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user import User
from tests.conftest import session_factory
from tests.helpers.posts import PostData, create_test_image, create_test_post


@pytest.mark.asyncio
async def test_update_post(client: AsyncClient):
    post = await create_test_post(client)

    response = await client.patch(
        f"/posts/{post['id']}",
        data={
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
async def test_update_post_replaces_file(
    client: AsyncClient,
):
    post = await create_test_post(client)

    response = await client.patch(
        f"/posts/{post['id']}",
        files={
            "file": (
                "new-image.jpg",
                create_test_image(),
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 200

    updated_post = cast(PostData, response.json())

    assert updated_post["id"] == post["id"]
    assert updated_post["file_name"] == "new-image.jpg"
    assert updated_post["file_type"] == "image/jpeg"
    assert updated_post["url"] != post["url"]


@pytest.mark.asyncio
async def test_update_post_not_found(client: AsyncClient):
    post_id = "00000000-0000-0000-0000-000000000000"

    response = await client.patch(
        f"/posts/{post_id}",
        data={
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
        data={"caption": "Updated caption"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to update this post"
    )


@pytest.mark.asyncio
async def test_update_post_replaces_file_and_deletes_old_file(
    client: AsyncClient,
):
    post = await create_test_post(client)

    old_url = post["url"]
    old_filename = Path(old_url).name
    old_file = Path("uploads") / old_filename

    assert old_file.exists()

    response = await client.patch(
        f"/posts/{post['id']}",
        files={
            "file": (
                "new-image.jpg",
                create_test_image(),
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 200

    updated_post = cast(PostData, response.json())

    assert updated_post["url"] != old_url

    assert not old_file.exists()


@pytest.mark.asyncio
async def test_update_post_rejects_invalid_replacement_and_preserves_old_file(
    client: AsyncClient,
):
    post = await create_test_post(client)

    old_url = post["url"]
    old_filename = Path(old_url).name
    old_file = Path("uploads") / old_filename

    assert old_file.exists()

    response = await client.patch(
        f"/posts/{post['id']}",
        files={
            "file": (
                "malicious.txt",
                b"not an image",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"

    assert old_file.exists()

    get_response = await client.get(f"/posts/{post['id']}")

    assert get_response.status_code == 200

    current_post = cast(PostData, get_response.json())

    assert current_post["url"] == old_url


@pytest.mark.asyncio
async def test_update_post_database_failure_does_not_delete_old_file(
    client: AsyncClient,
):
    post = await create_test_post(client)

    old_url = post["url"]
    old_filename = Path(old_url).name
    old_file = Path("uploads") / old_filename

    assert old_file.exists()

    async def failing_commit(self: AsyncSession) -> None:  # pyright: ignore[reportUnusedParameter]
        raise DatabaseError(
            "UPDATE posts",
            {},
            Exception("database connection failed"),
        )

    original_commit = AsyncSession.commit
    AsyncSession.commit = failing_commit

    try:
        response = await client.patch(
            f"/posts/{post['id']}",
            files={
                "file": (
                    "new-image.jpg",
                    create_test_image(),
                    "image/jpeg",
                ),
            },
        )
    finally:
        AsyncSession.commit = original_commit

    assert response.status_code == 500

    assert old_file.exists()


@pytest.mark.asyncio
async def test_update_post_database_failure_cleans_up_new_file(
    client: AsyncClient,
):
    post = await create_test_post(client)

    old_url = post["url"]
    old_filename = Path(old_url).name
    old_file = Path("uploads") / old_filename

    assert old_file.exists()

    existing_files = set(Path("uploads").glob("*.jpg"))

    async def failing_commit(self: AsyncSession) -> None:  # pyright: ignore[reportUnusedParameter]
        raise DatabaseError(
            "UPDATE posts",
            {},
            Exception("database connection failed"),
        )

    original_commit = AsyncSession.commit
    AsyncSession.commit = failing_commit

    try:
        response = await client.patch(
            f"/posts/{post['id']}",
            files={
                "file": (
                    "new-image.jpg",
                    create_test_image(),
                    "image/jpeg",
                ),
            },
        )
    finally:
        AsyncSession.commit = original_commit

    assert response.status_code == 500

    current_files = set(Path("uploads").glob("*.jpg"))
    new_files = current_files - existing_files

    assert old_file.exists()
    assert new_files == set()
