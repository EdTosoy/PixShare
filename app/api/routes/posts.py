import logging
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUserDep
from app.api.serialization import post_response, post_responses
from app.core.upload import validate_upload
from app.db.session import get_async_session
from app.models.post import Post
from app.schemas.post import PostResponse
from app.storage.base import Storage
from app.storage.dependencies import StorageDep

router = APIRouter(prefix="/posts", tags=["posts"])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]

LimitDep = Annotated[int, Query(ge=1, le=100)]
OffsetDep = Annotated[int, Query(ge=0)]
SortOrder = Literal["newest", "oldest"]
logger = logging.getLogger(__name__)


async def cleanup_media(storage: Storage, url: str) -> None:
    """A cleanup failure must not undo or disguise a committed database write."""
    try:
        await storage.delete(url)
    except Exception:  # noqa: BLE001 - committed writes survive any cleanup failure
        # URLs, exception text, and SQL parameters can contain private data.
        logger.error("Media cleanup failed; storage reconciliation required")


def ordered_posts(query: Select[tuple[Post]], sort: SortOrder) -> Select[tuple[Post]]:
    if sort == "newest":
        return query.order_by(Post.created_at.desc(), Post.id.desc())
    return query.order_by(Post.created_at.asc(), Post.id.asc())


@router.get(
    "",
    response_model=list[PostResponse],
)
async def get_posts(
    session: SessionDep,
    storage: StorageDep,
    limit: LimitDep = 20,
    offset: OffsetDep = 0,
    file_type: str | None = None,
    sort: SortOrder = "newest",
) -> list[PostResponse]:
    query = select(Post)

    if file_type is not None:
        query = query.where(Post.file_type == file_type)

    query = ordered_posts(query, sort).offset(offset).limit(limit)

    result = await session.execute(query)

    return await post_responses(list(result.scalars().all()), storage)


@router.get(
    "/{post_id}",
    response_model=PostResponse,
)
async def get_post_by_id(
    post_id: UUID,
    session: SessionDep,
    storage: StorageDep,
) -> PostResponse:
    post = await session.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return await post_response(post, storage)


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form(max_length=5000)] = None,
) -> PostResponse:
    await validate_upload(file)

    url = await storage.upload(
        file=file.file,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
    )

    post = Post(
        user_id=current_user.id,
        caption=caption,
        url=url,
        file_name=Path(file.filename or "upload").name[:255],
        file_type=file.content_type or "application/octet-stream",
    )

    session.add(post)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await cleanup_media(storage, url)
        raise
    await session.refresh(post)

    return await post_response(post, storage)


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
)
async def update_post(
    post_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
    file: Annotated[UploadFile | None, File()] = None,
    caption: Annotated[str | None, Form(max_length=5000)] = None,
) -> PostResponse:
    post = await session.get(Post, post_id, with_for_update=True)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this post",
        )

    if caption is not None or "caption" in await request.form():
        post.caption = caption or ""

    old_url: str | None = None
    new_url: str | None = None

    if file is not None:
        await validate_upload(file)

        old_url = post.url

        new_url = await storage.upload(
            file=file.file,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
        )

        post.url = new_url
        post.file_name = Path(file.filename or "upload").name[:255]
        post.file_type = file.content_type or "application/octet-stream"

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        if new_url is not None:
            await cleanup_media(storage, new_url)
        raise

    if old_url is not None:
        await cleanup_media(storage, old_url)
    await session.refresh(post)
    return await post_response(post, storage)


@router.delete(
    "/{post_id}",
    response_model=PostResponse,
)
async def delete_post(
    post_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
) -> PostResponse:
    post = await session.get(Post, post_id, with_for_update=True)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this post",
        )

    deleted = await post_response(post, storage)
    url = post.url
    await session.delete(post)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await cleanup_media(storage, url)
    return deleted
