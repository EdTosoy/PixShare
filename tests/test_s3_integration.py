"""Real S3 HTTP tests. Opt in only with a dedicated local *-test bucket."""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Unpack, cast
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from botocore.exceptions import ClientError, EndpointConnectionError
from dotenv import dotenv_values
from httpx import AsyncClient
from mypy_boto3_s3.type_defs import (
    DeleteObjectsOutputTypeDef,
    DeleteObjectsRequestTypeDef,
    PutObjectOutputTypeDef,
    PutObjectRequestTypeDef,
)
from PIL import Image
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.main import app
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostResponse
from app.storage.base import StorageUnavailable
from app.storage.dependencies import get_storage
from app.storage.reconcile import reconcile
from app.storage.router import MediaStorage
from app.storage.s3 import S3Storage
from tests.conftest import TEST_DATABASE_URL, session_factory
from tests.helpers.settings import IsolatedSettings

pytestmark = pytest.mark.skipif(os.environ.get("S3_INTEGRATION_TEST") != "1", reason="Requires an explicitly configured real local S3 test service")


def image_bytes(color: str = "navy") -> bytes:
    output = BytesIO()
    with Image.new("RGB", (800, 400), color) as image:
        image.save(output, "JPEG")
    return output.getvalue()


@pytest.fixture
def s3_settings(tmp_path: Path) -> Settings:
    env_file = os.environ.get("S3_INTEGRATION_ENV_FILE")
    if not env_file:
        pytest.fail("Set S3_INTEGRATION_ENV_FILE to an ignored dedicated local environment file")
    values = {key.lower(): value for key, value in dotenv_values(env_file).items() if value is not None}
    values.update(database_url=TEST_DATABASE_URL, uploads_dir=str(tmp_path), s3_prefix=f"phase9/tests/{uuid4().hex}")
    settings = IsolatedSettings.model_validate(values)
    if (
        not settings.s3_endpoint_url
        or urlsplit(settings.s3_endpoint_url).hostname not in {"127.0.0.1", "localhost", "minio"}
        or not settings.s3_bucket.endswith("-test")
        or not settings.s3_access_key_id
        or not settings.s3_secret_access_key
    ):
        pytest.fail("Refusing integration tests outside an explicit local *-test bucket")
    return settings


@pytest_asyncio.fixture
async def s3(s3_settings: Settings) -> AsyncGenerator[S3Storage, None]:
    storage = S3Storage(s3_settings)
    yield storage
    # Each test owns a unique namespace, never an entire bucket or user prefix.
    for group in await asyncio.to_thread(storage.list_groups):
        await asyncio.to_thread(storage.delete_group, group.prefix)


@pytest_asyncio.fixture
async def routed(s3: S3Storage, s3_settings: Settings) -> AsyncGenerator[MediaStorage, None]:
    storage = MediaStorage(s3_settings)
    storage.s3 = s3
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    _ = app.dependency_overrides.pop(get_storage, None)


@pytest.mark.asyncio
async def test_real_upload_public_reads_private_manifest_and_no_anonymous_mutations(s3: S3Storage):
    content = image_bytes()
    reference = await s3.upload(BytesIO(content), "untrusted.html", "image/jpeg")
    assert reference.startswith("s3://") and reference.endswith("original.jpg")
    info = await s3.describe(reference)
    assert info is not None and len(info.variants) == 3
    assert (info.width, info.height) == (800, 400)
    async with AsyncClient() as browser:
        original = await browser.get(s3.public_url(reference))
        assert original.status_code == 200 and original.content == content
        assert original.headers["content-type"] == "image/jpeg"
        for variant in info.variants:
            response = await browser.get(variant.url)
            assert response.status_code == 200 and response.headers["content-type"] == "image/webp"
            assert "immutable" in response.headers["cache-control"]
            with Image.open(BytesIO(response.content)) as image:
                assert image.size == (variant.width, variant.height)
        group = s3.reference_key(reference)
        assert group is not None
        manifest_url = s3.object_url(group.rsplit("/", 1)[0] + "/manifest.json")
        assert (await browser.get(manifest_url)).status_code == 403
        assert (await browser.get(s3.public_base + "?list-type=2")).status_code == 403
        assert (await browser.put(s3.public_url(reference), content=b"not authorized")).status_code == 403
        assert (await browser.delete(s3.public_url(reference))).status_code == 403
        assert (await browser.get(s3.public_url(reference))).content == content
    await s3.delete(reference)
    assert not await asyncio.to_thread(s3.group_keys, s3.prefix)


@pytest.mark.asyncio
async def test_unique_keys_and_collision_preserve_existing_group(s3: S3Storage):
    with patch("app.storage.s3.uuid4", return_value=UUID(int=9)):
        reference = await s3.upload(BytesIO(image_bytes()), "first.jpg", "image/jpeg")
        before = await asyncio.to_thread(s3.group_keys, s3.prefix)
        with pytest.raises(StorageUnavailable):
            _ = await s3.upload(BytesIO(image_bytes("red")), "second.jpg", "image/jpeg")
    assert await asyncio.to_thread(s3.group_keys, s3.prefix) == before
    async with AsyncClient() as browser:
        assert (await browser.get(s3.public_url(reference))).content == image_bytes()
    second = await s3.upload(BytesIO(image_bytes()), "first.jpg", "image/jpeg")
    assert second != reference


@pytest.mark.asyncio
async def test_ambiguous_original_put_is_cleaned_only_when_owned(s3: S3Storage):
    put = s3.client.put_object

    def timeout_after_write(**params: Unpack[PutObjectRequestTypeDef]) -> PutObjectOutputTypeDef:
        _ = put(**params)
        raise EndpointConnectionError(endpoint_url="http://private-diagnostic.invalid")

    with patch.object(s3.client, "put_object", timeout_after_write), pytest.raises(StorageUnavailable) as error:
        _ = await s3.upload(BytesIO(image_bytes()), "photo.jpg", "image/jpeg")
    assert "private-diagnostic" not in str(error.value)
    assert not await asyncio.to_thread(s3.group_keys, s3.prefix)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["variants/v1-640.webp", "manifest.json"])
async def test_failed_variant_publication_keeps_original_and_cleans_derivatives(s3: S3Storage, stage: str):
    put = s3.client.put_object

    def fail_put(**params: Unpack[PutObjectRequestTypeDef]) -> PutObjectOutputTypeDef:
        if params["Key"].endswith(stage):
            raise ClientError({"Error": {"Code": "InternalError", "Message": "simulated failure"}}, "PutObject")
        return put(**params)

    with patch.object(s3.client, "put_object", fail_put):
        reference = await s3.upload(BytesIO(image_bytes()), "photo.jpg", "image/jpeg")
    assert await s3.describe(reference) is None
    assert await asyncio.to_thread(s3.group_keys, s3.prefix) == [s3.reference_key(reference)]
    async with AsyncClient() as browser:
        assert (await browser.get(s3.public_url(reference))).status_code == 200


@pytest.mark.asyncio
async def test_encoder_failure_original_only_and_metadata_outage(s3: S3Storage):
    with patch("app.storage.s3.generate_variants", side_effect=OSError("simulated encoder failure")):
        reference = await s3.upload(BytesIO(image_bytes()), "photo.jpg", "image/jpeg")
    assert await s3.describe(reference) is None
    with patch.object(s3.client, "get_object", side_effect=EndpointConnectionError(endpoint_url="http://not-logged.invalid")):
        assert await s3.describe(reference) is None
    async with AsyncClient() as browser:
        assert (await browser.get(s3.public_url(reference))).status_code == 200


@pytest.mark.asyncio
async def test_partial_delete_response_is_retried_and_permanent_error_is_visible(s3: S3Storage):
    reference = await s3.upload(BytesIO(image_bytes()), "photo.jpg", "image/jpeg")
    real_delete = s3.client.delete_objects
    count = 0

    def partial_delete(**params: Unpack[DeleteObjectsRequestTypeDef]) -> DeleteObjectsOutputTypeDef:
        nonlocal count
        count += 1
        if count == 1:
            keys = list(params["Delete"]["Objects"])
            _ = real_delete(Bucket=params["Bucket"], Delete={"Objects": keys[1:], "Quiet": True})
            return cast(DeleteObjectsOutputTypeDef, cast(object, {"Errors": [{"Key": keys[0]["Key"], "Code": "InternalError"}]}))
        return real_delete(**params)

    with patch.object(s3.client, "delete_objects", partial_delete):
        await s3.delete(reference)
    assert count == 2 and not await asyncio.to_thread(s3.group_keys, s3.prefix)
    reference = await s3.upload(BytesIO(image_bytes()), "photo.jpg", "image/jpeg")
    key = s3.reference_key(reference)
    assert key is not None

    def denied_delete(**params: Unpack[DeleteObjectsRequestTypeDef]) -> DeleteObjectsOutputTypeDef:
        _ = real_delete(Bucket=s3.bucket, Delete={"Objects": [item for item in params["Delete"]["Objects"] if item["Key"] != key]})
        return cast(DeleteObjectsOutputTypeDef, cast(object, {"Errors": [{"Key": key, "Code": "AccessDenied"}]}))

    with patch.object(s3.client, "delete_objects", denied_delete), pytest.raises(StorageUnavailable):
        await s3.delete(reference)
    assert await asyncio.to_thread(s3.group_keys, s3.prefix) == [key]


@pytest.mark.asyncio
async def test_foreign_bucket_prefix_and_traversal_never_delete(s3: S3Storage):
    with patch.object(s3.client, "delete_objects", side_effect=AssertionError("must not reach SDK")):
        for reference in ["https://foreign.example/a.jpg", "s3://foreign/elsewhere/original.jpg", f"s3://{s3.bucket}/other/{'a'*32}/original.jpg", f"s3://{s3.bucket}/{s3.prefix}../original.jpg", f"s3://{s3.bucket}/{s3.prefix}{'a'*32}/original.jpg?token=secret"]:
            await s3.delete(reference)
            assert s3.reference_key(reference) is None


@pytest.mark.asyncio
async def test_router_preserves_local_legacy_and_s3_reads_after_provider_switch(routed: MediaStorage, s3: S3Storage):
    local = await routed.local.upload(BytesIO(image_bytes()), "legacy.jpg", "image/jpeg")
    assert routed.public_url(local) == local and await routed.describe(local) is not None
    reference = await routed.upload(BytesIO(image_bytes()), "new.jpg", "image/jpeg")
    assert reference.startswith("s3://")
    routed.provider = "local"
    assert routed.public_url(reference) == s3.public_url(reference)
    assert await routed.describe(reference) is not None
    again = await routed.upload(BytesIO(image_bytes()), "local.jpg", "image/jpeg")
    assert again.startswith("/uploads/")
    await routed.delete(local)
    await routed.delete(again)


@pytest.mark.asyncio
async def test_api_s3_roundtrip_replacement_legacy_and_delete(client: AsyncClient, routed: MediaStorage, s3: S3Storage):
    routed.provider = "local"
    response = await client.post("/posts", files={"file": ("legacy.jpg", image_bytes(), "image/jpeg")})
    legacy = PostResponse.model_validate(response.json())
    assert legacy.url.startswith("/uploads/")
    routed.provider = "s3"
    response = await client.patch(f"/posts/{legacy.id}", files={"file": ("new.jpg", image_bytes("red"), "image/jpeg")})
    assert response.status_code == 200
    current = PostResponse.model_validate(response.json())
    assert current.url.startswith(s3.public_base + "/") and current.image is not None
    async with session_factory() as session:
        record = await session.get(Post, legacy.id)
        assert record is not None and record.url.startswith("s3://")
    assert not (routed.local.upload_dir / Path(legacy.url).name).exists()
    assert (await client.get("/posts")).json()[0]["url"] == current.url
    assert (await client.get("/users/me/posts")).json()[0]["url"] == current.url
    assert (await client.delete(f"/posts/{legacy.id}")).status_code == 200
    async with AsyncClient() as browser:
        assert (await browser.get(current.url)).status_code == 404
        for variant in current.image.variants:
            assert (await browser.get(variant.url)).status_code == 404


@pytest.mark.asyncio
async def test_failed_commit_preserves_old_media_and_cleans_new_group(client: AsyncClient, routed: MediaStorage, s3: S3Storage):
    _ = routed
    response = await client.post("/posts", files={"file": ("photo.jpg", image_bytes(), "image/jpeg")})
    old = PostResponse.model_validate(response.json())
    before = await asyncio.to_thread(s3.group_keys, s3.prefix)

    async def fail_commit(_self: AsyncSession) -> None:
        raise DatabaseError("write", {}, Exception("simulated failure"))

    with patch.object(AsyncSession, "commit", fail_commit):
        failed = await client.post("/posts", files={"file": ("failed.jpg", image_bytes(), "image/jpeg")})
        assert failed.status_code == 500
        failed = await client.patch(f"/posts/{old.id}", files={"file": ("replacement.jpg", image_bytes("red"), "image/jpeg")})
        assert failed.status_code == 500
        failed = await client.delete(f"/posts/{old.id}")
        assert failed.status_code == 500
    assert await asyncio.to_thread(s3.group_keys, s3.prefix) == before
    assert PostResponse.model_validate((await client.get(f"/posts/{old.id}")).json()).url == old.url


@pytest.mark.asyncio
async def test_refresh_after_committed_replacement_retains_new_group(client: AsyncClient, routed: MediaStorage, s3: S3Storage):
    _ = routed, s3
    response = await client.post("/posts", files={"file": ("photo.jpg", image_bytes(), "image/jpeg")})
    old = PostResponse.model_validate(response.json())

    async def fail_refresh(_self: AsyncSession, _instance: object) -> None:
        raise DatabaseError("refresh", {}, Exception("simulated failure"))

    with patch.object(AsyncSession, "refresh", fail_refresh):
        response = await client.patch(f"/posts/{old.id}", files={"file": ("new.jpg", image_bytes("red"), "image/jpeg")})
    assert response.status_code == 500
    current = PostResponse.model_validate((await client.get(f"/posts/{old.id}")).json())
    assert current.url != old.url and current.image is not None
    async with AsyncClient() as browser:
        assert (await browser.get(current.url)).status_code == 200
        assert (await browser.get(old.url)).status_code == 404


@pytest.mark.asyncio
async def test_service_outage_is_sanitized_503_and_does_not_create_row(client: AsyncClient, routed: MediaStorage, s3: S3Storage):
    _ = routed
    with patch.object(s3.client, "put_object", side_effect=EndpointConnectionError(endpoint_url="http://private-endpoint.invalid")):
        response = await client.post("/posts", files={"file": ("photo.jpg", image_bytes(), "image/jpeg")})
    assert response.status_code == 503 and "private-endpoint" not in response.text
    assert (await client.get("/posts")).json() == []


@pytest.mark.asyncio
async def test_orphan_audit_grace_reference_checks_and_explicit_cleanup(s3: S3Storage, test_user: User):
    live = await s3.upload(BytesIO(image_bytes()), "live.jpg", "image/jpeg")
    orphan = await s3.upload(BytesIO(image_bytes()), "orphan.jpg", "image/jpeg")
    async with session_factory() as session:
        session.add(Post(user_id=test_user.id, url=live, file_name="live.jpg", file_type="image/jpeg"))
        await session.commit()
        recent, removed = await reconcile(s3, session, datetime.now(UTC) - timedelta(hours=24))
        assert recent == [] and removed == 0
        # Simulate passage of the grace period; object I/O remains real MinIO.
        cutoff = datetime.now(UTC) + timedelta(hours=24)
        candidates, removed = await reconcile(s3, session, cutoff)
        assert len(candidates) == 1 and removed == 0
        with pytest.raises(ValueError):
            _ = await reconcile(s3, session, cutoff, apply=True)
        _, removed = await reconcile(s3, session, cutoff, apply=True, writes_paused=True)
        assert removed == 1
    async with AsyncClient() as browser:
        assert (await browser.get(s3.public_url(live))).status_code == 200
        assert (await browser.get(s3.public_url(orphan))).status_code == 404
