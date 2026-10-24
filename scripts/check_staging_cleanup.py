"""Read-only verification of smoke-test objects. Never delete or list a bucket broadly."""

import argparse
import re
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class Arguments(argparse.Namespace):
    bucket: str = ""
    checkpoint: Path = Path()
    after_replacement: bool = False


class SmokeCheckpoint(BaseModel):
    groups: list[str]
    deleted: bool = False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--bucket", required=True)
    _ = parser.add_argument("--checkpoint", type=Path, required=True)
    _ = parser.add_argument("--after-replacement", action="store_true")
    args = parser.parse_args(namespace=Arguments())
    bucket = args.bucket
    checkpoint_path = args.checkpoint
    if not bucket.endswith("-staging") or checkpoint_path.is_symlink():
        parser.error("Use the isolated *-staging bucket and a private regular checkpoint")
    if checkpoint_path.stat().st_mode & 0o077:
        parser.error("Checkpoint must be private (0600)")
    checkpoint = SmokeCheckpoint.model_validate_json(checkpoint_path.read_text())
    groups = checkpoint.groups
    if len(groups) != 2 or any(
        not re.fullmatch(r"pixshare/staging/[a-f0-9]{32}/", group)
        for group in groups
    ):
        parser.error("Checkpoint must contain the two exact smoke media groups")
    if args.after_replacement:
        groups = groups[:1]
    elif not checkpoint.deleted:
        parser.error("Run smoke cleanup first, or specify --after-replacement")
    client: S3Client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3", config=Config(connect_timeout=3, read_timeout=10,
                            retries={"mode": "standard", "total_max_attempts": 3}),
    )
    for group in groups:
        response = client.list_objects_v2(Bucket=bucket, Prefix=group, MaxKeys=1)
        if response.get("KeyCount", 0):
            raise SystemExit("FAIL: smoke objects remain; review lifecycle/orphan recovery")
    print(f"PASS: {len(groups)} smoke groups have no current objects; historical versions are intentionally retained")


if __name__ == "__main__":
    try:
        main()
    except (BotoCoreError, ClientError, OSError, ValueError, TypeError):
        raise SystemExit("Cleanup verification failed; no credentials or SDK details logged") from None
