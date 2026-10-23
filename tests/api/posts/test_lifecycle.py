from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import UPLOADS_DIR
from app.models.post import Post
from app.schemas.post import PostResponse
from app.storage.local import LocalStorage
from tests.conftest import session_factory
from tests.helpers.posts import PostData, create_test_image, create_test_post


async def fail_commit(_self: AsyncSession) -> None:
    raise DatabaseError("write", {}, Exception("test failure"))


def media_files() -> set[Path]:
    return {path for path in UPLOADS_DIR.rglob("*") if path.is_file()}


@pytest.mark.asyncio
async def test_create_failure_cleans_new_upload(client: AsyncClient):
    before = media_files()
    with patch.object(AsyncSession, "commit", fail_commit):
        response = await client.post(
            "/posts", files={"file": ("image.jpg", create_test_image(), "image/jpeg")}
        )
    assert response.status_code == 500
    assert media_files() == before


@pytest.mark.asyncio
async def test_delete_failure_preserves_file_and_row(client: AsyncClient):
    post = await create_test_post(client)
    before = media_files()
    with patch.object(AsyncSession, "commit", fail_commit):
        response = await client.delete(f"/posts/{post['id']}")
    assert response.status_code == 500
    assert (UPLOADS_DIR / Path(post["url"]).name).exists()
    assert (await client.get(f"/posts/{post['id']}")).status_code == 200
    assert media_files() == before


@pytest.mark.asyncio
async def test_refresh_failure_keeps_committed_replacement(client: AsyncClient):
    post = await create_test_post(client)

    async def fail_refresh(_self: AsyncSession, _instance: object) -> None:
        raise DatabaseError("refresh", {}, Exception("test failure"))

    with patch.object(AsyncSession, "refresh", fail_refresh):
        response = await client.patch(
            f"/posts/{post['id']}",
            files={"file": ("new.jpg", create_test_image(), "image/jpeg")},
        )
    assert response.status_code == 500
    saved = cast(PostData, (await client.get(f"/posts/{post['id']}")).json())
    assert saved["url"] != post["url"]
    assert (UPLOADS_DIR / Path(saved["url"]).name).exists()
    response = PostResponse.model_validate((await client.get(f"/posts/{post['id']}")).json())
    assert response.image is not None and response.image.variants
    for variant in response.image.variants:
        assert (await client.get(variant.url)).status_code == 200
    assert not (UPLOADS_DIR / "_variants" / Path(post["url"]).name).exists()


@pytest.mark.asyncio
async def test_tied_timestamps_have_stable_pages(client: AsyncClient):
    from sqlalchemy import update

    for _ in range(5):
        _ = await create_test_post(client)
    async with session_factory() as session:
        _ = await session.execute(
            update(Post).values(created_at=datetime(2026, 1, 1, tzinfo=UTC))
        )
        await session.commit()
    ascending = cast(list[PostData], (await client.get("/posts?sort=oldest")).json())
    assert [p["id"] for p in ascending] == sorted(p["id"] for p in ascending)
    first = cast(list[PostData], (await client.get("/posts?limit=2")).json())
    second = cast(list[PostData], (await client.get("/posts?limit=3&offset=2")).json())
    assert [p["id"] for p in first + second] == sorted(
        (p["id"] for p in ascending), reverse=True
    )


@pytest.mark.asyncio
async def test_caption_can_be_cleared(client: AsyncClient):
    post = await create_test_post(client)
    response = await client.patch(f"/posts/{post['id']}", data={"caption": ""})
    assert response.status_code == 200
    assert response.json()["caption"] == ""


@pytest.mark.asyncio
async def test_cleanup_failure_preserves_committed_replacement(client: AsyncClient):
    post = await create_test_post(client)
    with patch.object(
        LocalStorage, "delete", AsyncMock(side_effect=OSError("test cleanup failure"))
    ):
        response = await client.patch(
            f"/posts/{post['id']}",
            files={"file": ("new.jpg", create_test_image(), "image/jpeg")},
        )
    assert response.status_code == 200
    saved = cast(PostData, response.json())
    assert saved["url"] != post["url"]
    assert (UPLOADS_DIR / Path(saved["url"]).name).exists()
    assert (await client.get(f"/posts/{post['id']}")).json()["url"] == saved["url"]
