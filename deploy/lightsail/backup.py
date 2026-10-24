"""Coordinated demo backups. Run only by the root-owned operations scripts.

Archives include private database/media data. Never upload them as CI artifacts.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tarfile
from pathlib import Path
from typing import IO, TYPE_CHECKING, Literal

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

RELEASE = "7bcac0f151c6b4773533238dfe11b0b5fd4659b5"
PREFIX = "pixshare/demo/"
MAX_BYTES = 512 * 1024 * 1024
WORK = Path("/work")


class ObjectSnapshot(BaseModel):
    key: str
    version_id: str
    file: str
    content_type: str
    cache_control: str | None
    metadata: dict[str, str]


class Manifest(BaseModel):
    format: Literal[1] = 1
    release: str = RELEASE
    files: dict[str, str]
    objects: list[ObjectSnapshot]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def client() -> S3Client:
    return boto3.client(  # pyright: ignore[reportUnknownMemberType] - only the S3 stubs are installed
        "s3",
        region_name=os.environ["S3_REGION"],
        config=Config(connect_timeout=3, read_timeout=30, retries={"max_attempts": 3}),
    )


def collect() -> None:
    snapshot = WORK / "snapshot"
    snapshot.mkdir(mode=0o700)
    for name in ["database.dump", "rows.fingerprints"]:
        _ = shutil.copyfile(WORK / name, snapshot / name)
    total = sum(path.stat().st_size for path in snapshot.iterdir())
    if total > MAX_BYTES:
        raise ValueError("Database backup exceeds the reviewed demo size budget")
    objects: list[ObjectSnapshot] = []
    s3 = client()
    bucket = os.environ["S3_BUCKET"]
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            key = obj.get("Key")
            if not key or not key.startswith(PREFIX):
                raise ValueError("Unexpected object key")
            name = f"objects/{hashlib.sha256(key.encode()).hexdigest()}"
            path = snapshot / name
            path.parent.mkdir(mode=0o700, exist_ok=True)
            response = s3.get_object(Bucket=bucket, Key=key)
            if not response.get("VersionId") or response["VersionId"] == "null":
                raise ValueError("Versioning is required")
            with response["Body"] as body, path.open("xb") as output:
                while chunk := body.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("Backup exceeds the reviewed demo size budget")
                    _ = output.write(chunk)
            objects.append(ObjectSnapshot(
                key=key, version_id=response["VersionId"], file=name,
                content_type=response["ContentType"],
                cache_control=response.get("CacheControl"),
                metadata=response.get("Metadata", {}),
            ))
    legacy = Path("/legacy")
    for original in legacy.rglob("*"):
        if original.is_symlink():
            raise ValueError("Symlinks are not supported in media backups")
        if original.is_file():
            total += original.stat().st_size
            if total > MAX_BYTES:
                raise ValueError("Backup exceeds the reviewed demo size budget")
            target = snapshot / "legacy" / original.relative_to(legacy)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _ = shutil.copyfile(original, target)
    files = {str(path.relative_to(snapshot)): digest(path) for path in snapshot.rglob("*") if path.is_file()}
    manifest = Manifest(files=files, objects=objects)
    _ = (snapshot / "manifest.json").write_text(manifest.model_dump_json())
    with tarfile.open(WORK / "backup.tar.gz", "w:gz") as archive:
        for path in sorted(snapshot.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=str(path.relative_to(snapshot)), recursive=False)
    print("Coordinated archive created; API may resume.")


def archive_file(archive: tarfile.TarFile, name: str) -> IO[bytes]:
    stream = archive.extractfile(name)
    if stream is None:
        raise ValueError("Missing regular archive file")
    return stream


def verify() -> None:
    # Do not extract an archive wholesale, follow links or trust archive paths.
    target = WORK / "verified"
    with tarfile.open(WORK / "backup.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or any(not member.isfile() for member in members):
            raise ValueError("Unsupported archive members")
        if sum(member.size for member in members) > MAX_BYTES + 1024 * 1024:
            raise ValueError("Archive exceeds the reviewed size budget")
        manifest_member = archive.getmember("manifest.json")
        if manifest_member.size > 1024 * 1024:
            raise ValueError("Oversized manifest")
        with archive_file(archive, "manifest.json") as source:
            manifest = Manifest.model_validate_json(source.read())
        if manifest.release != RELEASE:
            raise ValueError("Unsupported backup release")
        if set(names) != set(manifest.files) | {"manifest.json"}:
            raise ValueError("Incomplete archive")
        if not {"database.dump", "rows.fingerprints"}.issubset(manifest.files):
            raise ValueError("Missing database snapshot")
        for name, expected in manifest.files.items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe archive path")
            checksum = hashlib.sha256()
            with archive_file(archive, name) as stream:
                while chunk := stream.read(1024 * 1024):
                    checksum.update(chunk)
            actual = checksum.hexdigest()
            if actual != expected:
                raise ValueError("Archive checksum mismatch")
        # Publish restore inputs only after EVERY media/database checksum passed.
        target.mkdir(mode=0o700)
        for name in ["database.dump", "rows.fingerprints"]:
            with archive_file(archive, name) as source, (target / name).open("xb") as output:
                shutil.copyfileobj(source, output)
    print("All database, legacy and S3 object checksums verified.")


def upload() -> None:
    archive = WORK / "backup.tar.gz"
    checksum = digest(archive)
    key = f"pixshare/backups/{os.environ['BACKUP_ID']}/backup.tar.gz"
    s3 = client()
    with archive.open("rb") as body:
        _ = s3.put_object(
            Bucket=os.environ["S3_BUCKET"], Key=key, Body=body,
            ContentType="application/gzip", ServerSideEncryption="AES256",
            Metadata={"sha256": checksum, "release": RELEASE},
        )
    stored = s3.head_object(Bucket=os.environ["S3_BUCKET"], Key=key)
    if stored["Metadata"].get("sha256") != checksum or stored["ContentLength"] != archive.stat().st_size:
        raise ValueError("Backup upload verification failed")
    print("Private versioned S3 backup uploaded and metadata verified.")


if __name__ == "__main__":
    try:
        commands = {"collect": collect, "verify": verify, "upload": upload}
        commands[sys.argv[1]]()
    except (BotoCoreError, ClientError, OSError, ValueError, KeyError, IndexError, TypeError, tarfile.TarError):
        # SDK exception text can contain object paths or credentials.
        print("Backup operation failed; retain private artifacts for operator review.", file=sys.stderr)
        sys.exit(1)
