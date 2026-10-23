"""Real Clerk SDK signature verification and HTTP/database authorization.

Ephemeral signing keys are test-only; no authentication dependency is replaced.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import cast

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.db.session import get_async_session
from app.main import app
from tests.conftest import override_get_async_session
from tests.helpers.posts import PostData, create_test_image

SignedClient = tuple[AsyncClient, str, str, str, str]


@pytest_asyncio.fixture
async def signed_client() -> AsyncGenerator[SignedClient, None]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    settings = Settings(
        database_url="postgresql+asyncpg://unused/unused",
        clerk_jwt_key=public,
        clerk_authorized_parties=["http://localhost:3000"],
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = override_get_async_session

    def token(
        subject: str, origin: str = "http://localhost:3000", seconds: int = 300
    ) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": subject,
                "sid": "test_session",
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(seconds=seconds),
                "azp": origin,
            },
            key,
            algorithm="RS256",
        )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield (
                client,
                token("owner_token_test"),
                token("other_token_test"),
                token("owner_token_test", origin="https://foreign.example"),
                token("owner_token_test", seconds=-100),
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_signed_http_crud_and_ownership(
    signed_client: SignedClient,
):
    client, owner_token, other_token, _, _ = signed_client
    owner = {"Authorization": f"Bearer {owner_token}"}
    other = {"Authorization": f"Bearer {other_token}"}
    assert (await client.get("/posts")).status_code == 200
    assert (await client.get("/users/me/posts")).status_code == 401
    assert (
        await client.get("/users/me", headers={"Authorization": "Bearer invalid"})
    ).status_code == 401
    created = await client.post(
        "/posts",
        headers=owner,
        data={"caption": "Signed upload"},
        files={"file": ("signed.jpg", create_test_image(), "image/jpeg")},
    )
    assert created.status_code == 201
    post = cast(PostData, created.json())
    identifier = post["id"]
    mine = cast(
        list[PostData], (await client.get("/users/me/posts", headers=owner)).json()
    )
    assert [p["id"] for p in mine] == [identifier]
    assert (await client.get("/users/me/posts", headers=other)).json() == []
    assert (
        await client.patch(
            f"/posts/{identifier}", headers=other, data={"caption": "forbidden"}
        )
    ).status_code == 403
    assert (
        await client.delete(f"/posts/{identifier}", headers=other)
    ).status_code == 403
    updated = await client.patch(
        f"/posts/{identifier}",
        headers=owner,
        data={"caption": "Updated"},
        files={"file": ("replace.jpg", create_test_image(), "image/jpeg")},
    )
    assert updated.status_code == 200
    assert updated.json()["caption"] == "Updated"
    assert updated.json()["url"] != post["url"]
    assert (
        await client.get("/users/me/posts?file_type=image/png", headers=owner)
    ).json() == []
    assert (
        await client.delete(f"/posts/{identifier}", headers=owner)
    ).status_code == 200
    assert (await client.get(f"/posts/{identifier}")).status_code == 404


@pytest.mark.asyncio
async def test_rejects_expired_wrong_origin_and_wrong_signature(
    signed_client: SignedClient,
):
    client, token, _, wrong_origin, expired = signed_client
    # Decode is used only to construct invalid test fixtures, never by application auth.
    claims = cast(
        dict[str, object], jwt.decode(token, options={"verify_signature": False})
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_signature = jwt.encode(claims, key, algorithm="RS256")
    for invalid in [wrong_signature, "not-a-jwt", wrong_origin, expired]:
        response = await client.get(
            "/users/me", headers={"Authorization": f"Bearer {invalid}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized"
