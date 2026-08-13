#!/usr/bin/env python3
"""
Seed script for PixShare.

Usage:
  export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/pixshare"
  python scripts/seed_db.py
"""

import os
import asyncio
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import your models (ensure PYTHONPATH includes repo root or run via `python -m scripts.seed_db`)
from app.models.user import User
from app.models.post import Post

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL (e.g. postgresql+asyncpg://user:pass@host/db)")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def seed():
    async with AsyncSessionLocal() as session:
        # Create a demo user
        demo_clerk_id = "demo_user_1"
        user = User(clerk_id=demo_clerk_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create a few posts for the user
        sample_posts = [
            {
                "caption": "Sunset demo image",
                "url": "/uploads/sample_sunset.jpg",
                "file_name": "sample_sunset.jpg",
                "file_type": "image/jpeg",
            },
            {
                "caption": "City demo image",
                "url": "/uploads/sample_city.png",
                "file_name": "sample_city.png",
                "file_type": "image/png",
            },
            {
                "caption": "Artwork demo image",
                "url": "/uploads/sample_art.webp",
                "file_name": "sample_art.webp",
                "file_type": "image/webp",
            },
        ]

        for p in sample_posts:
            post = Post(
                user_id=user.id,
                caption=p["caption"],
                url=p["url"],
                file_name=p["file_name"],
                file_type=p["file_type"],
            )
            session.add(post)

        await session.commit()
        print(f"Seeded demo user {user.clerk_id} and {len(sample_posts)} posts.")


if __name__ == "__main__":
    asyncio.run(seed())
