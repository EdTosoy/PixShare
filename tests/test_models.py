import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.post import Post
from app.models.user import User
from tests.conftest import session_factory


@pytest.mark.asyncio
async def test_user_clerk_id_must_be_unique():
    clerk_id = "duplicate_clerk_id"

    async with session_factory() as session:
        session.add(User(clerk_id=clerk_id))
        await session.commit()

    async with session_factory() as session:
        session.add(User(clerk_id=clerk_id))

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_user_clerk_id_cannot_be_null():
    async with session_factory() as session:
        session.add(User(clerk_id=None))

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_deleting_user_deletes_posts():
    async with session_factory() as session:
        user = User(clerk_id=f"cascade-test-{uuid.uuid4()}")

        session.add(user)
        await session.flush()

        post = Post(
            user_id=user.id,
            url="/uploads/test.jpg",
            file_name="test.jpg",
            file_type="image/jpeg",
        )

        session.add(post)
        await session.commit()

        post_id = post.id
        user_id = user.id

    async with session_factory() as session:
        user = await session.get(User, user_id)

        assert user is not None

        await session.delete(user)
        await session.commit()

    async with session_factory() as session:
        deleted_post = await session.get(Post, post_id)

        assert deleted_post is None


@pytest.mark.asyncio
async def test_user_post_relationship():
    async with session_factory() as session:
        user = User(clerk_id=f"relationship-test-{uuid.uuid4()}")

        post = Post(
            user=user,
            url="/uploads/test.jpg",
            file_name="test.jpg",
            file_type="image/jpeg",
        )

        session.add(user)
        session.add(post)
        await session.commit()

        post_id = post.id
        user_id = user.id

    async with session_factory() as session:
        post = await session.get(Post, post_id)

        assert post is not None
        assert post.user_id == user_id
