"""
Seed script for PixShare.

Usage:
    docker compose exec api uv run python -m scripts.seed_db

The script:
- Creates the demo user if it does not exist.
- Copies demo images from /app/demo to /app/uploads.
- Creates database records for demo images if they do not exist.
- Is safe to run multiple times.
"""

import asyncio
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.post import Post
from app.models.user import User
from app.storage.local import LocalStorage

settings = get_settings()
DATABASE_URL = settings.database_url

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

DEMO_CLERK_ID = "demo_user_1"

DEMO_DIR = Path(__file__).resolve().parents[1] / "demo"
UPLOADS_DIR = Path(settings.uploads_dir)

SAMPLE_POSTS = [
    {
        "caption": "Sunset demo image",
        "file_name": "sample_sunset.jpg",
        "file_type": "image/jpeg",
    },
    {
        "caption": "City demo image",
        "file_name": "sample_city.png",
        "file_type": "image/png",
    },
    {
        "caption": "Artwork demo image",
        "file_name": "sample_art.webp",
        "file_type": "image/webp",
    },
]


async def seed() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    storage = LocalStorage(str(UPLOADS_DIR))

    async with AsyncSessionLocal() as session:
        # Get or create the demo user.
        result = await session.execute(
            select(User).where(User.clerk_id == DEMO_CLERK_ID)
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(clerk_id=DEMO_CLERK_ID)
            session.add(user)
            await session.flush()

            print(f"Created demo user: {DEMO_CLERK_ID}")
        else:
            print(f"Using existing demo user: {DEMO_CLERK_ID}")

        posts_created = 0
        files_copied = 0

        for sample in SAMPLE_POSTS:
            file_name = sample["file_name"]

            source_path = DEMO_DIR / file_name
            upload_path = UPLOADS_DIR / file_name
            post_url = f"/uploads/{file_name}"

            if not source_path.is_file():
                raise FileNotFoundError(f"Demo file not found: {source_path}")

            # Copy the fixture into runtime storage if necessary.
            if not upload_path.exists():
                _ = shutil.copy2(source_path, upload_path)
                files_copied += 1

            _ = await storage.ensure_variants(post_url)

            # Check whether this demo post already exists.
            result = await session.execute(
                select(Post).where(
                    Post.user_id == user.id,
                    Post.file_name == file_name,
                )
            )

            post = result.scalar_one_or_none()

            if post is None:
                session.add(
                    Post(
                        user_id=user.id,
                        caption=sample["caption"],
                        url=post_url,
                        file_name=file_name,
                        file_type=sample["file_type"],
                    )
                )

                posts_created += 1

        await session.commit()

        message = (
            f"Seed complete: user={DEMO_CLERK_ID}, "
            f"files_copied={files_copied}, "
            f"posts_created={posts_created}"
        )

        print(message)


async def main() -> None:
    try:
        await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
