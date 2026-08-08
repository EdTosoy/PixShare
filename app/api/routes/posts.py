from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models.post import Post
from app.schemas.post import PostCreate, PostResponse, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    post_data: PostCreate,
    session: SessionDep,
) -> Post:
    post = Post(**post_data.model_dump())

    session.add(post)
    await session.commit()
    await session.refresh(post)

    return post


@router.get(
    "",
    response_model=list[PostResponse],
)
async def get_posts(
    session: SessionDep,
) -> list[Post]:
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))

    return list(result.scalars().all())


@router.get(
    "/{post_id}",
    response_model=PostResponse,
)
async def get_post_by_id(
    post_id: UUID,
    session: SessionDep,
) -> Post:
    post = await session.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return post


@router.delete(
    "/{post_id}",
    response_model=PostResponse,
)
async def delete_post(
    post_id: UUID,
    session: SessionDep,
) -> Post:
    result = await session.execute(
        delete(Post).where(Post.id == post_id).returning(Post)
    )

    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    await session.commit()

    return post


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
)
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    session: SessionDep,
) -> Post:
    post = await session.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    update_data = post_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    await session.commit()
    await session.refresh(post)

    return post
