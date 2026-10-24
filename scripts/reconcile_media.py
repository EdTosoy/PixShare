"""Dry-run by default; applying requires paused writes and a reviewed namespace."""

import argparse
import asyncio
import json
import math
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.storage.base import StorageUnavailable
from app.storage.reconcile import reconcile
from app.storage.s3 import S3Storage


class Arguments(argparse.Namespace):
    min_age_hours: float = 24
    report: Path = Path()
    apply: bool = False
    writes_paused: bool = False


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--min-age-hours", type=float, default=24)
    _ = parser.add_argument("--report", type=Path, required=True)
    _ = parser.add_argument("--apply", action="store_true")
    _ = parser.add_argument("--writes-paused", action="store_true")
    args = parser.parse_args(namespace=Arguments())
    if not math.isfinite(args.min_age_hours) or args.min_age_hours < 1 or (args.apply and not args.writes_paused):
        parser.error("Use at least one hour of grace; --apply requires --writes-paused")
    settings = get_settings()
    if not settings.s3_bucket:
        parser.error("Configure the intended S3 bucket and prefix first")
    storage = S3Storage(settings)
    # Reserve a private, writable report before any destructive operation.
    # Existing reports are never overwritten, especially after applying cleanup.
    fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        async with async_session_factory() as session:
            candidates, removed = await reconcile(
                storage, session, datetime.now(UTC) - timedelta(hours=args.min_age_hours),
                apply=args.apply, writes_paused=args.writes_paused,
            )
        # Inventory is for local operator review, never stdout or a browser response.
        report = {"bucket": storage.bucket, "prefix": storage.prefix,
                  "candidates": [asdict(group) for group in candidates], "removed": removed}
        json.dump(report, output, default=str, indent=2)
    print(f"Orphan groups: {len(candidates)}; removed: {removed}; private report saved")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (StorageUnavailable, BotoCoreError, ClientError, SQLAlchemyError, OSError):
        raise SystemExit("Storage reconciliation failed; no SDK details logged") from None
