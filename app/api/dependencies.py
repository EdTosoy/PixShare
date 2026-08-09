from typing import Annotated

from clerk_backend_api.security.types import RequestState
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import require_auth
from app.db.session import get_async_session
from app.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
AuthDep = Annotated[RequestState, Depends(require_auth)]


async def get_current_user(
    state: AuthDep,
    session: SessionDep,
) -> User:
    if state.payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication payload",
        )

    clerk_id = state.payload.get("sub")

    if not isinstance(clerk_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk user ID",
        )

    result = await session.execute(select(User).where(User.clerk_id == clerk_id))

    user = result.scalar_one_or_none()

    if user is None:
        user = User(clerk_id=clerk_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
