from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUserDep
from app.core.upload import validate_upload
from app.db.session import get_async_session
from app.models.post import Post
from app.schemas.post import PostResponse
from app.storage.dependencies import StorageDep

router = APIRouter(prefix="/posts", tags=["posts"])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]

LimitDep = Annotated[int, Query(ge=1, le=100)]
OffsetDep = Annotated[int, Query(ge=0)]
SortOrder = Literal["newest", "oldest"]


@router.get(
    "",
    response_model=list[PostResponse],
)
async def get_posts(
    session: SessionDep,
    limit: LimitDep = 20,
    offset: OffsetDep = 0,
    file_type: str | None = None,
    sort: SortOrder = "newest",
) -> list[Post]:
    query = select(Post)

    if file_type is not None:
        query = query.where(Post.file_type == file_type)

    if sort == "newest":
        query = query.order_by(Post.created_at.desc())
    else:
        query = query.order_by(Post.created_at.asc())

    query = query.offset(offset).limit(limit)

    result = await session.execute(query)

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


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
    file: UploadFile = File(...),
    caption: str | None = Form(None),
) -> Post:
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
        file_name=file.filename or "upload",
        file_type=file.content_type or "application/octet-stream",
    )

    session.add(post)
    await session.commit()
    await session.refresh(post)

    return post


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
)
async def update_post(
    post_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
    file: UploadFile | None = File(None),
    caption: str | None = Form(None),
) -> Post:
    post = await session.get(Post, post_id)

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

    if caption is not None:
        post.caption = caption

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
        post.file_name = file.filename or "upload"
        post.file_type = file.content_type or "application/octet-stream"

    try:
        await session.commit()
        await session.refresh(post)
    except Exception:
        if new_url is not None:
            await storage.delete(new_url)

        raise

    if old_url is not None:
        await storage.delete(old_url)

    return post


@router.delete(
    "/{post_id}",
    response_model=PostResponse,
)
async def delete_post(
    post_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    storage: StorageDep,
) -> Post:
    post = await session.get(Post, post_id)

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this post",
        )

    await storage.delete(post.url)

    await session.delete(post)
    await session.commit()

    return post
