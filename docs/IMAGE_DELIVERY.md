# Image delivery and API compatibility

Post endpoints retain all existing fields and return an additional nullable
`image` object. There is no database migration or URL rewrite:

```json
{
  "url": "/uploads/example.jpg",
  "image": {
    "width": 2400,
    "height": 1200,
    "variants": [
      {"url": "/uploads/_variants/example.jpg/v1-320.webp", "width": 320, "height": 160},
      {"url": "/uploads/_variants/example.jpg/v1-640.webp", "width": 640, "height": 320},
      {"url": "/uploads/_variants/example.jpg/v1-1280.webp", "width": 1280, "height": 640},
      {"url": "/uploads/_variants/example.jpg/v1-1920.webp", "width": 1920, "height": 960}
    ]
  }
}
```

This is a partial example, not a replacement for the other post fields.
`image.width/height` describe the oriented source. Variant dimensions are their
actual pixel dimensions; the size in each filename is its **longest edge**.
Portrait variants therefore have smaller width descriptors. All derivatives
keep aspect ratio, never upscale, normalize EXIF orientation, preserve alpha,
and omit source EXIF/GPS. RGB/RGBA color profiles are preserved rather than
silently changing their color space; profiled non-RGB sources keep original
delivery to avoid attaching a CMYK/gray profile to converted RGB pixels.
Originals remain byte-for-byte unchanged, including
their metadata. Output uses Pillow WebP quality 80, method 4. Images smaller
than 320px receive one native-size derivative. Animated WebP stays original-only
to preserve animation.

All public post reads, personal-gallery reads, and successful mutations use this
additive schema. Older clients can keep using `url`. Unsupported adapters,
legacy images, missing/corrupt bundles, and encoding failures produce
`"image": null`. GET never decodes or generates media. OpenAPI at `/docs`
includes the `ImageInfo` and `ImageVariant` models.

## Bounds and publication

New uploads accept JPEG/PNG/WebP, verified MIME/format agreement, up to 10 MiB,
16,000,000 pixels and 20,000px on either side. Dimension checks happen before
pixel loading. Pillow decompression-bomb warnings/errors still reject uploads;
they are not disabled. Dimension violations return HTTP 400 with actionable
limits. Existing images over the budget remain readable at their original URLs.

Validation and generation run in worker threads sharing a process-local lock.
Only one PixShare image decode/resize runs per API process at a time; each output
is bounded to a maximum 1920px edge. Images and intermediate rasters close after
use. This bounds per-job raster work; ingress concurrency/body limits and the
number of API worker processes still determine aggregate deployment memory.

The local storage adapter writes originals with exclusive creation. A collision
must never unlink an existing original. Derivatives and a small manifest are
created in a temporary sibling directory and renamed into place together.
The API advertises a bundle only when its manifest and every referenced file
exist. A failed optional generation removes partial derivatives and keeps the
original available; it logs an aggregate warning without paths or exceptions.
It does not claim optimization succeeded or retry encoding during reads.

Versioned derivative URLs use `Cache-Control: public, max-age=31536000, immutable`.
Changes to encoder policy must bump the variant version and produce new URLs.
Original delivery retains its existing ETag/Last-Modified behavior. Cache hits
may outlive physical deletion, as with any public media; cached URLs are not an
authorization mechanism.

## Replacement, deletion, and failure

`Storage.upload()` returns the original URL and owns its derivative bundle.
`Storage.describe()` optionally exposes the bundle without changing models.
`Storage.delete(original_url)` attempts both original and bundle cleanup, even
when removing the original fails. Only local `/uploads/` filenames are accepted;
foreign URLs and traversal are ignored, and bundle symlinks are not followed.

The API preserves its existing transaction order and row locking. A failed
database commit cleans every new object and retains old media. Successful
replacement/deletion commits before removing old objects. A later refresh
failure never deletes a committed replacement. Post-commit cleanup failures
remain sanitized reconciliation warnings. PostgreSQL and the filesystem cannot
share a transaction; crashes and storage failures can still leave orphans.
See [production limitations](PRODUCTION.md).

## Existing uploads and local backfill

No startup job or migration touches existing images. They continue to work with
`image: null`. To optimize them explicitly with the correct local database and
upload directory configured in the environment, run from the repository root:

```bash
uv run --no-sync python -m scripts.backfill_variants
```

This reads one post under its existing row lock, generates only a missing or
incomplete compatible bundle, and leaves original bytes and database fields
unchanged. The lock serializes backfill with replacement/deletion, avoiding old
bundles being recreated after a delete. Complete bundles are skipped, making
repeated runs idempotent. Output is aggregate `ready`, `original_only`, and
`removed` counts; over-budget, animated, profiled non-RGB, missing, or unsupported sources remain
original-only. Inspect warning counts rather than treating those as optimized.
The seed script also prepares bounded variants for its bundled images.

Backfill was exercised only against disposable Phase 8 data in this session.
No backfill was run against the user's existing application database or uploads.

## Frontend selection and fallback

`PostImage` combines `picture/source` with Next Image. The browser chooses from
actual-width WebP descriptors according to responsive `sizes` and its pixel
density; it can still load the original if WebP is unsupported, metadata is null,
or a derivative request fails. Gallery sources load lazily; details/editor
previews load eagerly. Existing CSS reserves the image frame before loading.
The browser directly fetches public media from the API, so no Next private-IP
optimizer allowance or new image service is needed.

See [Phase 8 measurements and verification](PHASE_8_REPORT.md) for actual payload
reductions, the retained large legacy fixture, test results, and browser limits.
