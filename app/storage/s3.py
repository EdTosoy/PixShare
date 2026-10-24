"""S3-compatible immutable media groups; no bucket provisioning or public writes."""

import asyncio
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, BinaryIO, final, override
from urllib.parse import quote, urlsplit
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from app.core.config import Settings
from app.core.upload import MAX_FILE_SIZE
from app.schemas.media import ImageInfo
from app.storage.base import Storage, StorageUnavailable
from app.storage.variants import generate_variants

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

logger = logging.getLogger(__name__)
MAX_MANIFEST_BYTES = 16_384
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"


@dataclass(frozen=True)
class MediaGroup:
    prefix: str
    modified_at: datetime
    object_count: int


@final
class S3Storage(Storage):
    def __init__(self, settings: Settings):
        self.bucket = settings.s3_bucket
        self.prefix = settings.s3_prefix + "/"
        self.public_base = settings.s3_public_base_url
        self.attempts = settings.s3_max_attempts
        try:
            self.client: S3Client = boto3.client(  # pyright: ignore[reportUnknownMemberType] - only S3 SDK stubs are installed
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key_id.get_secret_value() if settings.s3_access_key_id else None,
                aws_secret_access_key=settings.s3_secret_access_key.get_secret_value() if settings.s3_secret_access_key else None,
                aws_session_token=settings.s3_session_token.get_secret_value() if settings.s3_session_token else None,
                config=Config(
                    signature_version="s3v4",
                    connect_timeout=settings.s3_connect_timeout,
                    read_timeout=settings.s3_read_timeout,
                    retries={"mode": "standard", "total_max_attempts": self.attempts},
                    s3={"addressing_style": settings.s3_addressing_style},
                    ignore_configured_endpoint_urls=True,  # pyright: ignore[reportCallIssue] - supported by installed botocore; absent in its stubs
                ),
            )
        except (BotoCoreError, ClientError, ValueError):
            raise StorageUnavailable("Media storage client could not be initialized") from None

    def reference_key(self, reference: str) -> str | None:
        parsed = urlsplit(reference)
        if parsed.scheme != "s3" or parsed.netloc != self.bucket or parsed.query or parsed.fragment:
            return None
        key = parsed.path.removeprefix("/")
        if not re.fullmatch(re.escape(self.prefix) + r"[a-f0-9]{32}/original\.(?:jpg|png|webp)", key):
            return None
        return key

    @override
    def public_url(self, reference: str) -> str:
        key = self.reference_key(reference)
        if key is None:
            raise StorageUnavailable("Media reference does not belong to configured storage")
        return self.object_url(key)

    def object_url(self, key: str) -> str:
        return f"{self.public_base}/{quote(key, safe='/')}"

    def reference(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    def owns_original(self, key: str, operation: str) -> bool:
        try:
            result = self.client.head_object(Bucket=self.bucket, Key=key)
            return result.get("Metadata", {}).get("pixshare-upload") == operation
        except (BotoCoreError, ClientError):
            return False

    def delete_keys(self, keys: list[str]) -> None:
        failed = False
        for offset in range(0, len(keys), 1000):
            pending = keys[offset:offset + 1000]
            for attempt in range(self.attempts):
                try:
                    result = self.client.delete_objects(
                        Bucket=self.bucket,
                        Delete={"Objects": [{"Key": key} for key in pending], "Quiet": True},
                    )
                except (BotoCoreError, ClientError):
                    failed = True
                    break
                errors = result.get("Errors", [])
                if not errors:
                    break
                transient = {"InternalError", "SlowDown", "ServiceUnavailable", "RequestTimeout"}
                retryable = [error["Key"] for error in errors if error.get("Code") in transient and "Key" in error]
                if len(retryable) != len(errors):
                    failed = True
                if attempt + 1 == self.attempts:
                    failed = True
                if not retryable:
                    break
                pending = retryable
        if failed:
            raise StorageUnavailable("Some media objects could not be removed")

    def group_keys(self, prefix: str) -> list[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        return [item["Key"] for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix)
                for item in page.get("Contents", []) if "Key" in item]

    def delete_group(self, prefix: str) -> None:
        self.delete_keys(self.group_keys(prefix))

    def upload_sync(self, file: BinaryIO, content_type: str) -> str:
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(content_type)
        if extension is None:
            raise StorageUnavailable("Unsupported media type")
        content = file.read(MAX_FILE_SIZE + 1)
        if not content or len(content) > MAX_FILE_SIZE:
            raise StorageUnavailable("Invalid media size")
        group = f"{self.prefix}{uuid4().hex}/"
        key = group + f"original.{extension}"
        operation = secrets.token_hex(16)
        owned = False
        try:
            with TemporaryDirectory(prefix="pixshare-s3-") as temporary:
                source = Path(temporary) / f"original.{extension}"
                _ = source.write_bytes(content)
                bundle = Path(temporary) / "variants"
                info: ImageInfo | None = None
                try:
                    info = generate_variants(source, bundle, group + "variants")
                except Exception:  # noqa: BLE001 - derivatives are optional; original remains usable
                    logger.warning("Image variants unavailable; original retained")
                try:
                    _ = self.client.put_object(
                        Bucket=self.bucket, Key=key, Body=content, ContentType=content_type,
                        IfNoneMatch="*", Metadata={"pixshare-upload": operation},
                        CacheControl=IMMUTABLE_CACHE,
                    )
                    owned = True
                except (BotoCoreError, ClientError):
                    # A timed-out PUT may have succeeded. Clean it only when its
                    # private operation marker proves this request created it.
                    owned = self.owns_original(key, operation)
                    raise
                if info is not None:
                    planned = [variant.url for variant in info.variants] + [group + "manifest.json"]
                    try:
                        for variant in info.variants:
                            with (bundle / Path(variant.url).name).open("rb") as body:
                                _ = self.client.put_object(
                                    Bucket=self.bucket, Key=variant.url, Body=body,
                                    ContentType="image/webp", CacheControl=IMMUTABLE_CACHE,
                                    IfNoneMatch="*",
                                )
                        _ = self.client.put_object(
                            Bucket=self.bucket, Key=group + "manifest.json",
                            Body=info.model_dump_json().encode(), ContentType="application/json",
                            CacheControl="no-store", IfNoneMatch="*",
                        )
                    except (BotoCoreError, ClientError, OSError):
                        # Never advertise a partial bundle, including an ambiguous
                        # manifest PUT. Cleanup failures remain auditable orphans.
                        try:
                            # Remove the publication marker before its children.
                            # If this fails, retain the complete set rather than
                            # leave a published manifest pointing at removed data.
                            _ = self.client.delete_object(Bucket=self.bucket, Key=group + "manifest.json")
                            self.delete_keys(planned[:-1])
                        except (BotoCoreError, ClientError, StorageUnavailable):
                            logger.error("Variant cleanup failed; storage reconciliation required")
                        logger.warning("Object variants unavailable; original retained")
                return self.reference(key)
        except (BotoCoreError, ClientError, OSError):
            if owned:
                try:
                    self.delete_group(group)
                except (BotoCoreError, ClientError, StorageUnavailable):
                    logger.error("Upload cleanup failed; storage reconciliation required")
            raise StorageUnavailable("Media upload could not be completed") from None

    @override
    async def upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        return await asyncio.to_thread(self.upload_sync, file, content_type)

    @override
    async def delete(self, url: str) -> None:
        key = self.reference_key(url)
        if key is None:
            return
        try:
            await asyncio.to_thread(self.delete_group, key.rsplit("/", 1)[0] + "/")
        except (BotoCoreError, ClientError):
            raise StorageUnavailable("Media cleanup could not be completed") from None

    def describe_sync(self, key: str) -> ImageInfo | None:
        group = key.rsplit("/", 1)[0] + "/"
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=group + "manifest.json")
            body = response["Body"]
            try:
                data = body.read(MAX_MANIFEST_BYTES + 1)
            finally:
                body.close()
            if len(data) > MAX_MANIFEST_BYTES:
                return None
            info = ImageInfo.model_validate_json(data)
            if not 1 <= len(info.variants) <= 4:
                return None
            for variant in info.variants:
                if not re.fullmatch(re.escape(group) + r"variants/v1-\d+\.webp", variant.url):
                    return None
                variant.url = self.object_url(variant.url)
            return info
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"NoSuchKey", "404"}:
                logger.warning("Object metadata unavailable; original delivery retained")
            return None
        except (BotoCoreError, OSError, ValueError, ValidationError):
            logger.warning("Object metadata unavailable; original delivery retained")
            return None

    @override
    async def describe(self, url: str) -> ImageInfo | None:
        key = self.reference_key(url)
        return await asyncio.to_thread(self.describe_sync, key) if key else None

    def list_groups(self, within: str | None = None) -> list[MediaGroup]:
        if within is not None and not re.fullmatch(re.escape(self.prefix) + r"[a-f0-9]{32}/", within):
            return []
        groups: dict[str, MediaGroup] = {}
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=within or self.prefix):
            for item in page.get("Contents", []):
                key, modified = item.get("Key"), item.get("LastModified")
                if key is None or modified is None:
                    continue
                match = re.fullmatch(re.escape(self.prefix) + r"([a-f0-9]{32})/.+", key)
                if match is None:
                    continue
                prefix = self.prefix + match[1] + "/"
                old = groups.get(prefix)
                groups[prefix] = MediaGroup(prefix, max(old.modified_at, modified) if old else modified,
                                           old.object_count + 1 if old else 1)
        return list(groups.values())
