from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUserDep, SessionDep
from app.api.routes.posts import LimitDep, OffsetDep, SortOrder, ordered_posts
from app.api.serialization import post_responses
from app.models.post import Post
from app.schemas.post import PostResponse
from app.schemas.user import UserResponse
from app.storage.dependencies import StorageDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUserDep):
    return current_user


@router.get("/me/posts", response_model=list[PostResponse])
async def get_my_posts(
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
    limit: LimitDep = 20,
    offset: OffsetDep = 0,
    file_type: str | None = None,
    sort: SortOrder = "newest",
) -> list[PostResponse]:
    query = select(Post).where(Post.user_id == current_user.id)
    if file_type is not None:
        query = query.where(Post.file_type == file_type)
    result = await session.execute(
        ordered_posts(query, sort).offset(offset).limit(limit)
    )
    return await post_responses(list(result.scalars().all()), storage)
