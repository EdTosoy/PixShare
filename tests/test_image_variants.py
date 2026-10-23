from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import images
from app.main import UPLOADS_DIR
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostResponse
from app.storage.local import LocalStorage
from tests.conftest import session_factory
from tests.helpers.posts import create_test_post


def photo(size: tuple[int, int] = (2400, 1200), mode: str = "RGB") -> bytes:
    with Image.new(mode, size, (30, 100, 180, 80) if mode == "RGBA" else "navy") as image:
        output = BytesIO()
        image.save(output, "PNG" if mode == "RGBA" else "JPEG")
        return output.getvalue()


def files(root: Path) -> set[Path]:
    return {path for path in root.rglob("*") if path.is_file()}


@pytest.mark.asyncio
async def test_variants_preserve_original_aspect_and_are_bounded(tmp_path: Path):
    original = photo()
    storage = LocalStorage(str(tmp_path))
    url = await storage.upload(BytesIO(original), "photo.jpg", "image/jpeg")
    assert (tmp_path / Path(url).name).read_bytes() == original
    info = await storage.describe(url)
    assert info is not None
    assert (info.width, info.height) == (2400, 1200)
    assert [(v.width, v.height) for v in info.variants] == [
        (320, 160), (640, 320), (1280, 640), (1920, 960)
    ]
    for variant in info.variants:
        with Image.open(tmp_path / variant.url.removeprefix("/uploads/")) as image:
            assert image.format == "WEBP"
            assert image.size == (variant.width, variant.height)
            assert not image.getexif()
    before = files(tmp_path)
    await storage.delete(url)
    assert not files(tmp_path)
    assert len(before) == 6  # original, four variants, manifest


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(40, 80), (1200, 2400), (2400, 1200)])
async def test_variants_do_not_upscale_or_change_portrait_ratio(tmp_path: Path, size: tuple[int, int]):
    storage = LocalStorage(str(tmp_path))
    url = await storage.upload(BytesIO(photo(size)), "photo.jpg", "image/jpeg")
    info = await storage.describe(url)
    assert info is not None
    assert all(v.width <= size[0] and v.height <= size[1] for v in info.variants)
    assert all(v.width / v.height == size[0] / size[1] for v in info.variants)
    if max(size) < 320:
        assert len(info.variants) == 1


@pytest.mark.asyncio
async def test_variant_transparency_and_exif_orientation(tmp_path: Path):
    storage = LocalStorage(str(tmp_path))
    url = await storage.upload(BytesIO(photo((80, 40), "RGBA")), "alpha.png", "image/png")
    info = await storage.describe(url)
    assert info is not None
    with Image.open(tmp_path / info.variants[0].url.removeprefix("/uploads/")) as image:
        assert image.mode == "RGBA"
        assert image.getchannel("A").getextrema() == (80, 80)
    with Image.new("RGB", (80, 40), "red") as image:
        exif = image.getexif()
        exif[274] = 6
        output = BytesIO()
        image.save(output, "JPEG", exif=exif)
    content = output.getvalue()
    url = await storage.upload(BytesIO(content), "rotated.jpg", "image/jpeg")
    info = await storage.describe(url)
    assert info is not None
    assert (info.width, info.height) == (40, 80)
    assert (tmp_path / Path(url).name).read_bytes() == content


@pytest.mark.asyncio
async def test_rgb_profile_is_preserved_and_profiled_non_rgb_stays_original(tmp_path: Path):
    # Reuse the actual bundled photograph's profile without decoding its pixels.
    with Image.open(Path(__file__).resolve().parents[1] / "demo/sample_sunset.jpg") as sample:
        profile = cast(bytes, sample.info["icc_profile"])
    storage = LocalStorage(str(tmp_path))
    with Image.new("RGB", (80, 40), "red") as image:
        output = BytesIO()
        image.save(output, "JPEG", icc_profile=profile)
    url = await storage.upload(BytesIO(output.getvalue()), "profile.jpg", "image/jpeg")
    info = await storage.describe(url)
    assert info is not None
    with Image.open(tmp_path / info.variants[0].url.removeprefix("/uploads/")) as image:
        assert image.info["icc_profile"] == profile
    with Image.new("CMYK", (80, 40), "black") as image:
        output = BytesIO()
        image.save(output, "JPEG", icc_profile=profile)
    content = output.getvalue()
    url = await storage.upload(BytesIO(content), "cmyk.jpg", "image/jpeg")
    assert await storage.describe(url) is None
    assert (tmp_path / Path(url).name).read_bytes() == content


@pytest.mark.asyncio
async def test_mid_generation_failure_retains_only_original(tmp_path: Path):
    storage = LocalStorage(str(tmp_path))
    content = photo()
    save = Image.Image.save
    calls = 0

    def failing_save(self: Image.Image, fp: str | Path, format: str | None = None, **params: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated encoder failure")
        save(self, fp, format, **params)

    with patch.object(Image.Image, "save", failing_save):
        url = await storage.upload(BytesIO(content), "photo.jpg", "image/jpeg")
    original = tmp_path / Path(url).name
    assert original.read_bytes() == content
    assert files(tmp_path) == {original}
    assert await storage.describe(url) is None
    # Explicit retry/backfill is safe and idempotent; GET never retries encoding.
    assert await storage.ensure_variants(url) is not None
    before = {p: p.stat().st_mtime_ns for p in files(tmp_path)}
    assert await storage.ensure_variants(url) is not None
    assert before == {p: p.stat().st_mtime_ns for p in files(tmp_path)}


@pytest.mark.asyncio
async def test_missing_or_corrupt_manifest_falls_back_and_can_be_rebuilt(tmp_path: Path):
    storage = LocalStorage(str(tmp_path))
    url = await storage.upload(BytesIO(photo()), "photo.jpg", "image/jpeg")
    info = await storage.describe(url)
    assert info is not None
    (tmp_path / info.variants[0].url.removeprefix("/uploads/")).unlink()
    assert await storage.describe(url) is None
    assert await storage.ensure_variants(url) is not None
    manifest = tmp_path / "_variants" / Path(url).name / "manifest.json"
    _ = manifest.write_text("invalid json")
    assert await storage.describe(url) is None
    assert await storage.ensure_variants(url) is not None


@pytest.mark.asyncio
async def test_animated_and_over_budget_legacy_images_remain_originals(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage = LocalStorage(str(tmp_path))
    with Image.new("RGB", (20, 20), "red") as first, Image.new("RGB", (20, 20), "blue") as second:
        content = BytesIO()
        first.save(content, "WEBP", save_all=True, append_images=[second], duration=100, loop=0)
    url = await storage.upload(BytesIO(content.getvalue()), "motion.webp", "image/webp")
    assert await storage.describe(url) is None
    with Image.open(tmp_path / Path(url).name) as image:
        assert getattr(image, "is_animated", False)
    monkeypatch.setattr(images, "MAX_SOURCE_PIXELS", 100)
    url = await storage.upload(BytesIO(photo((20, 20))), "legacy.jpg", "image/jpeg")
    assert await storage.describe(url) is None
    assert (tmp_path / Path(url).name).is_file()


@pytest.mark.asyncio
async def test_delete_still_removes_variants_if_original_unlink_fails(tmp_path: Path):
    storage = LocalStorage(str(tmp_path))
    url = await storage.upload(BytesIO(photo()), "photo.jpg", "image/jpeg")
    original = tmp_path / Path(url).name
    unlink = Path.unlink

    def failing_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == original:
            raise PermissionError("simulated unlink failure")
        unlink(self, missing_ok=missing_ok)

    with patch.object(Path, "unlink", failing_unlink), pytest.raises(PermissionError):
        await storage.delete(url)
    assert files(tmp_path) == {original}


@pytest.mark.asyncio
async def test_legacy_api_record_and_backfill_do_not_change_original(client: AsyncClient, test_user: User):
    legacy = UPLOADS_DIR / "phase8-legacy.jpg"
    content = photo((80, 40))
    _ = legacy.write_bytes(content)
    async with session_factory() as session:
        post = Post(user_id=test_user.id, url="/uploads/phase8-legacy.jpg", file_name="legacy.jpg", file_type="image/jpeg")
        session.add(post)
        await session.commit()
        await session.refresh(post)
        post_id = post.id
    response = await client.get(f"/posts/{post_id}")
    assert response.status_code == 200
    saved = PostResponse.model_validate(response.json())
    assert saved.image is None
    assert (await client.get(saved.url)).content == content
    info = await LocalStorage(str(UPLOADS_DIR)).ensure_variants("/uploads/phase8-legacy.jpg")
    assert info is not None
    updated = PostResponse.model_validate((await client.get(f"/posts/{post_id}")).json())
    assert updated.url == saved.url
    assert updated.image is not None and updated.image.width == 80
    assert legacy.read_bytes() == content
    assert (await client.delete(f"/posts/{post_id}")).status_code == 200
    assert not legacy.exists()


@pytest.mark.asyncio
async def test_new_api_variants_are_public_cached_and_removed_with_post(client: AsyncClient):
    post = await create_test_post(client)
    response = PostResponse.model_validate((await client.get(f"/posts/{post['id']}")).json())
    assert response.image is not None
    variant = response.image.variants[0]
    public = await client.get(variant.url)
    assert public.status_code == 200
    assert public.headers["content-type"] == "image/webp"
    assert "immutable" in public.headers["cache-control"]
    assert (await client.get("/posts")).json()[0]["image"] == response.image.model_dump()
    assert (await client.get("/users/me/posts")).json()[0]["image"] == response.image.model_dump()
    assert (await client.delete(f"/posts/{post['id']}")).status_code == 200
    assert (await client.get(variant.url)).status_code == 404


@pytest.mark.asyncio
async def test_api_encoder_failure_still_persists_original(client: AsyncClient):
    with patch("app.storage.local.generate_variants", side_effect=OSError("simulated failure")):
        post = await create_test_post(client)
    response = PostResponse.model_validate((await client.get(f"/posts/{post['id']}")).json())
    assert response.image is None
    assert (await client.get(post["url"])).status_code == 200


@pytest.mark.asyncio
async def test_decode_budget_is_checked_before_loading_pixels(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    content = photo((20, 20))
    monkeypatch.setattr(images, "MAX_SOURCE_PIXELS", 100)
    with patch.object(Image.Image, "load", side_effect=AssertionError("must not decode")):
        response = await client.post("/posts", files={"file": ("large.jpg", content, "image/jpeg")})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_failed_replacement_commit_cleans_every_new_variant(client: AsyncClient):
    post = await create_test_post(client)
    before = files(UPLOADS_DIR)

    async def fail_commit(_self: AsyncSession) -> None:
        raise DatabaseError("write", {}, Exception("simulated failure"))

    with patch.object(AsyncSession, "commit", fail_commit):
        response = await client.patch(f"/posts/{post['id']}", files={"file": ("new.jpg", photo(), "image/jpeg")})
    assert response.status_code == 500
    assert files(UPLOADS_DIR) == before
    saved = PostResponse.model_validate((await client.get(f"/posts/{post['id']}")).json())
    assert saved.url == post["url"] and saved.image is not None


@pytest.mark.asyncio
async def test_successful_replacement_removes_every_old_variant(client: AsyncClient):
    post = await create_test_post(client)
    before = PostResponse.model_validate((await client.get(f"/posts/{post['id']}")).json())
    assert before.image is not None
    response = await client.patch(f"/posts/{post['id']}", files={"file": ("new.jpg", photo(), "image/jpeg")})
    assert response.status_code == 200
    after = PostResponse.model_validate(response.json())
    assert after.image is not None
    for url in [before.url, *(variant.url for variant in before.image.variants)]:
        assert (await client.get(url)).status_code == 404
    for variant in after.image.variants:
        assert (await client.get(variant.url)).status_code == 200
    assert (await client.delete(f"/posts/{post['id']}")).status_code == 200
    for url in [after.url, *(variant.url for variant in after.image.variants)]:
        assert (await client.get(url)).status_code == 404


@pytest.mark.asyncio
async def test_encoder_failure_during_replacement_keeps_new_original(client: AsyncClient):
    post = await create_test_post(client)
    content = photo()
    with patch("app.storage.local.generate_variants", side_effect=OSError("simulated failure")):
        response = await client.patch(f"/posts/{post['id']}", files={"file": ("new.jpg", content, "image/jpeg")})
    assert response.status_code == 200
    saved = PostResponse.model_validate(response.json())
    assert saved.url != post["url"] and saved.image is None
    assert (await client.get(saved.url)).content == content
    assert (await client.get(post["url"])).status_code == 404


@pytest.mark.asyncio
async def test_original_write_failure_removes_partial_file(tmp_path: Path):
    storage = LocalStorage(str(tmp_path))
    with patch("app.storage.local.shutil.copyfileobj", side_effect=OSError("simulated disk failure")), pytest.raises(OSError):
        _ = await storage.upload(BytesIO(photo()), "photo.jpg", "image/jpeg")
    assert not files(tmp_path)


@pytest.mark.asyncio
async def test_filename_collision_never_deletes_existing_original_or_variants(tmp_path: Path):
    storage = LocalStorage(str(tmp_path))
    content = photo((80, 40))
    with patch("app.storage.local.uuid4", return_value=UUID(int=8)):
        url = await storage.upload(BytesIO(content), "photo.jpg", "image/jpeg")
        before = files(tmp_path)
        with pytest.raises(FileExistsError):
            _ = await storage.upload(BytesIO(photo((40, 80))), "photo.jpg", "image/jpeg")
    assert (tmp_path / Path(url).name).read_bytes() == content
    assert await storage.describe(url) is not None
    assert files(tmp_path) == before
