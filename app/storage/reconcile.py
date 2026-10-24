"""Operator-invoked orphan audit. Never run automatically on startup or reads."""

import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.storage.s3 import MediaGroup, S3Storage


async def reconcile(
    storage: S3Storage,
    session: AsyncSession,
    older_than: datetime,
    *,
    apply: bool = False,
    writes_paused: bool = False,
) -> tuple[list[MediaGroup], int]:
    if apply and not writes_paused:
        raise ValueError("Pause application writes before applying orphan cleanup")
    references = (await session.scalars(select(Post.url))).all()
    live_groups = {
        key.rsplit("/", 1)[0] + "/"
        for reference in references
        if (key := storage.reference_key(reference)) is not None
    }
    groups = await asyncio.to_thread(storage.list_groups)
    candidates = [group for group in groups if group.prefix not in live_groups and group.modified_at < older_than]
    removed = 0
    if apply:
        for group in candidates:
            refreshed = await asyncio.to_thread(storage.list_groups, group.prefix)
            if not refreshed or refreshed[0].modified_at >= older_than:
                continue
            # Fresh READ COMMITTED check, even after the operator paused writes.
            referenced = await session.scalar(
                select(Post.id).where(Post.url.like(f"s3://{storage.bucket}/{group.prefix}original.%")).limit(1)
            )
            if referenced is None:
                await asyncio.to_thread(storage.delete_group, group.prefix)
                removed += 1
    return candidates, removed
