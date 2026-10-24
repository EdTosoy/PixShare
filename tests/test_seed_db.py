from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.post import Post
from app.storage.local import LocalStorage
from scripts import seed_db
from tests.conftest import session_factory


@pytest.mark.asyncio
async def test_demo_seed_normalizes_new_copies_and_preserves_existing_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    demo = tmp_path / "demo"
    uploads = tmp_path / "uploads"
    demo.mkdir()
    for sample in seed_db.SAMPLE_POSTS:
        # Reproduce the historical JPEG bytes behind PNG/WebP suffixes.
        with Image.new("RGB", (2000, 1000), "navy") as image:
            image.save(demo / sample["file_name"], format="JPEG")
    originals = {p.name: p.read_bytes() for p in demo.iterdir()}
    monkeypatch.setattr(seed_db, "DEMO_DIR", demo)
    monkeypatch.setattr(seed_db, "UPLOADS_DIR", uploads)
    monkeypatch.setattr(seed_db, "AsyncSessionLocal", session_factory)

    await seed_db.seed()
    storage = LocalStorage(str(uploads))
    formats = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
    for sample in seed_db.SAMPLE_POSTS:
        with Image.open(uploads / sample["file_name"]) as image:
            assert image.format == formats[sample["file_type"]]
            assert image.size == (1920, 960)
        assert await storage.describe(f"/uploads/{sample['file_name']}") is not None
        assert (demo / sample["file_name"]).read_bytes() == originals[sample["file_name"]]

    preserved = {p.name: p.read_bytes() for p in uploads.iterdir() if p.is_file()}
    await seed_db.seed()
    assert {p.name: p.read_bytes() for p in uploads.iterdir() if p.is_file()} == preserved
    async with session_factory() as session:
        assert len((await session.scalars(select(Post))).all()) == 3
