"""Explicit, nondestructive local backfill. No schema migration or read-time work."""

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.post import Post
from app.storage.local import LocalStorage


async def main() -> None:
    storage = LocalStorage(get_settings().uploads_dir)
    counts = {"ready": 0, "original_only": 0, "removed": 0}
    async with async_session_factory() as session:
        ids = list((await session.scalars(select(Post.id))).all())
    for post_id in ids:
        async with async_session_factory() as session:
            # Serialize with owner replacement/deletion; never resurrect old assets.
            post = await session.get(Post, post_id, with_for_update=True)
            if post is None:
                counts["removed"] += 1
                continue
            info = await storage.ensure_variants(post.url)
            counts["ready" if info else "original_only"] += 1
    # Aggregate counts only; filenames and account details are not logged.
    print(counts)


if __name__ == "__main__":
    asyncio.run(main())
