from unittest.mock import patch

import pytest
from clerk_backend_api.security.types import AuthStatus, RequestState
from fastapi import HTTPException, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.api.routes.auth import require_auth
from app.core.config import Settings
from app.main import app
from app.models.user import User
from tests.conftest import session_factory


@pytest.mark.asyncio
async def test_get_current_user_creates_new_user():
    clerk_id = "new_test_clerk_user"

    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload={"sub": clerk_id},
    )

    async with session_factory() as session:
        user = await get_current_user(
            state=state,
            session=session,
        )

        assert user.clerk_id == clerk_id
        assert user.id is not None

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.clerk_id == clerk_id))

        saved_user = result.scalar_one_or_none()

    assert saved_user is not None
    assert saved_user.id == user.id
    assert saved_user.clerk_id == clerk_id


@pytest.mark.asyncio
async def test_get_current_user_returns_existing_user(
    test_user: User,
):
    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload={"sub": test_user.clerk_id},
    )

    async with session_factory() as session:
        user = await get_current_user(
            state=state,
            session=session,
        )

    assert user.id == test_user.id
    assert user.clerk_id == test_user.clerk_id


@pytest.mark.asyncio
async def test_get_current_user_reuses_existing_user(
    test_user: User,
):
    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload={"sub": test_user.clerk_id},
    )

    async with session_factory() as session:
        first_user = await get_current_user(
            state=state,
            session=session,
        )

    async with session_factory() as session:
        second_user = await get_current_user(
            state=state,
            session=session,
        )

    assert first_user.id == test_user.id
    assert second_user.id == test_user.id
    assert first_user.id == second_user.id


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_payload():
    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload=None,
    )

    async with session_factory() as session:
        with pytest.raises(HTTPException) as exc_info:
            _ = await get_current_user(
                state=state,
                session=session,
            )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication payload"


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_clerk_id():
    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload={"sub": None},
    )

    async with session_factory() as session:
        with pytest.raises(HTTPException) as exc_info:
            _ = await get_current_user(
                state=state,
                session=session,
            )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid Clerk user ID"


@pytest.mark.asyncio
async def test_require_auth_rejects_unsigned_in_request():
    state = RequestState(
        status=AuthStatus.SIGNED_OUT,
        payload=None,
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1234),
            "scheme": "http",
        }
    )

    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        clerk_publishable_key="test",
        clerk_secret_key="test",
    )

    with (
        patch(
            "app.api.routes.auth.authenticate_request",
            return_value=state,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        _ = require_auth(
            request=request,
            settings=settings,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_require_auth_returns_signed_in_state():
    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload={"sub": "test_clerk_user"},
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1234),
            "scheme": "http",
        }
    )

    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        clerk_publishable_key="test",
        clerk_secret_key="test",
    )

    with patch(
        "app.api.routes.auth.authenticate_request",
        return_value=state,
    ):
        result = require_auth(
            request=request,
            settings=settings,
        )

    assert result is state
    assert result.is_signed_in
    assert result.payload == {"sub": "test_clerk_user"}


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_unauthenticated_request():
    state = RequestState(
        status=AuthStatus.SIGNED_OUT,
        payload=None,
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        with patch(
            "app.api.routes.auth.authenticate_request",
            return_value=state,
        ):
            response = await client.post(
                "/posts",
                files={
                    "file": (
                        "image.jpg",
                        b"fake image content",
                        "image/jpeg",
                    ),
                },
            )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_get_current_user_propagates_database_error():
    clerk_id = "database_error_test_user"

    state = RequestState(
        status=AuthStatus.SIGNED_IN,
        payload={"sub": clerk_id},
    )

    async with session_factory() as session:
        original_commit = session.commit

        async def failing_commit() -> None:
            raise RuntimeError("Database commit failed")

        session.commit = failing_commit  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="Database commit failed"):
            _ = await get_current_user(
                state=state,
                session=session,
            )

        session.commit = original_commit
