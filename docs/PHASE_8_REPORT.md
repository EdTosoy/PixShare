# Phase 8 — accessibility, image performance, and browser reliability

Recorded 2026-10-23. This phase preserves the existing design, original files,
Clerk authentication, ownership checks, and Alembic history. No commits, pushes,
deployments, cloud resources, or changes to existing user data were made.

## Findings and changes

| Finding | Implemented change |
| --- | --- |
| Gallery images downloaded full originals, even into small cards. | Generate bounded WebP variants locally and let the browser select actual-width responsive sources. Original URLs and bytes are retained. |
| Pillow's default bomb threshold allowed much larger raster allocations than this MVP needs; validation decoded on the event loop. | Check new uploads against 10 MiB, 16 MP, and 20,000px per side before loading pixels. Validation and generation run off-loop under one process-local image-work lock. Pillow bomb warnings/errors remain enabled. |
| Optional encoding must not jeopardize a valid original or a committed write. | Publish complete variant bundles atomically, discard partial derivatives on failure, expose original-only fallback, and delete bundles with their original using the existing transaction order. |
| Original exclusive-write failure could unlink an existing file on a filename collision. | Track whether this request actually created the file before removing a partial write. A collision regression preserves both original and variants. |
| Source photographs carry ICC profiles. Dropping them risks changing color-managed rendering. | Preserve RGB/RGBA profiles in WebP. Profiled non-RGB sources retain original delivery rather than receiving an incompatible RGB profile. Originals retain all metadata. |
| Small secondary labels reduced readability. | Card format and eyebrow labels: 9/10px → 12px. Form hints/upload help: 11px → 13px. Filter labels/detail metadata: 12px → 14px. Layout, palette, and content hierarchy remain established. |
| Card images repeated the adjacent caption in accessible names; empty captions used filenames, and long captions produced verbose descriptions. | Give card links concise caption-based names and their enclosed images empty decorative alt text. Detail/editor descriptions normalize whitespace and stop at 160 characters. Fallbacks are **Shared image** and **Untitled image**, with full captions/filenames still available on details. |
| Axe found contrast failures in Clerk's secondary/branding text. | Use the supported appearance variables with theme-aware secondary color and 14px base type. Authentication remains Clerk's actual UI. |
| Select and textarea boundaries used decorative colors: about 1.34:1 light / 1.42:1 dark against their fill. | Use the existing muted token for control boundaries. Regression checks require at least 3:1 against both fill and page background. Decorative separators retain their existing styling. |
| Native modal reverse-Tab navigation moved focus from Keep image to the browser outside the dialog in Chromium. | Explicitly wrap Tab/Shift+Tab between the two actions while retaining native modality, initial safe focus, Escape handling, and focus return. This was reproduced before repair and verified afterward. |
| Form errors lacked explicit invalid state/focus feedback. | File errors set `aria-invalid` and retain help/error associations. Server errors receive keyboard focus, forms expose `aria-busy`, and pending status distinguishes saving from uploading. |
| Clerk's testing SDK can log token-bearing URLs during shutdown/retry. | Test-only diagnostics now strip URL queries/session identifiers and response bodies, redact known keys/addresses and bearer/JWT/password patterns, and retain the diagnostic message. A setup regression checks redaction. No authentication behavior is changed. |

The working tree already contained previous-phase changes. Phase 8 is focused on
the media pipeline, responsive/accessible image components, accessibility styles
and form/dialog behavior, related tests, audit tooling, and documentation. The
only direct dependency addition is test-only `axe-core` 4.13.0, already present
transitively. Pinned pnpm 11.11.0 and the existing store installed it without
disabling supply-chain/signature checks. No backend dependency was added.

## Image architecture and API compatibility

See [image delivery/API documentation](IMAGE_DELIVERY.md) and the updated
[architecture](ARCHITECTURE.md). The original `url` remains the database reference.
Post responses add nullable `image` dimensions and a list of `{url,width,height}`
variants. Older clients and records continue using the original.

New bundles use maximum edges **320, 640, 1280, 1920px**, WebP quality 80/method 4,
original aspect ratio, no upscaling, normalized orientation, preserved alpha and
compatible color profiles. EXIF/GPS is omitted from derivatives. The original
is never recompressed or rewritten. Animated, over-budget legacy, and profiled
non-RGB images retain original delivery. An unavailable encoder or incomplete
manifest also falls back safely. GET requests never perform image generation.

`LocalStorage` owns originals, temporary work, manifests, and derivative cleanup.
`Storage.describe()` keeps metadata behind the storage interface. Existing row
locking and commit-before-cleanup order remain intact. Refresh failure after a
committed replacement cannot delete it. Versioned immutable derivative URLs have
long-lived cache headers; original delivery retains its existing behavior.

An explicit `uv run --no-sync python -m scripts.backfill_variants` command performs
idempotent, row-locked, nondestructive backfill. It was exercised only on fresh
Phase 8 test data: two bundled images optimized, one remained original-only.
The 7254 × 4841 city fixture exceeds 16 MP and remains functional unchanged.
The seed script now prepares variants for compatible demo images as well.

The frontend uses `picture/source` with Next Image original fallbacks, actual
variant width descriptors, and layout-specific `sizes`. Gallery images remain
lazy; details/editor previews are eager. Tests observe `currentSrc`, successful
decode, stable reserved frames while real image requests are delayed, and actual
original fallback when derivative requests fail. No server-side private-IP
optimizer bypass or new image service was introduced.

## Accessibility verification

Automated checks use axe-core WCAG 2.0/2.1/2.2 A/AA tags plus best practices,
without rule exclusions. The full browser suite includes **54 axe scans**:
42 public scans (seven routes × two themes × three device profiles), plus 12
authenticated page/state scans. Additional contrast assertions inspect visible
select/textarea borders, because axe does not establish every non-text contrast
requirement. A separate audit records 24 representative public/owner states.

| Coverage | Result |
| --- | --- |
| Public landing, Explore, detail, protected upload/gallery guidance, real sign-in and sign-up forms | PASS in light/dark at desktop/tablet/mobile profiles. |
| Authenticated upload, invalid file state, successful details, deletion dialog, editor, personal gallery | PASS in both themes, with genuine Clerk sessions. |
| File-control focus outline and Tab to caption; skip link and visible keyboard focus | PASS with actual keyboard events. |
| Dialog initial focus, reverse/forward wrapping, Escape, return to Delete | PASS after the reproduced repair. |
| Server-error focus, invalid-file state, recovery, long-caption disclosure and bounded alt | PASS. |
| Theme persistence, 390px reflow, reduced-motion transitions | PASS. |
| Final rendered control boundary contrast | PASS — approximately 5.40:1 light / 7.03:1 dark against fill, and 5.13:1 / 7.95:1 against page backgrounds. |
| Separate 24-state final audit | PASS — 24 states, zero reported axe violations; inconclusive counts retained. |

Some axe contrast checks remain **inconclusive**, not automatic passes. Reviewed
public cases include the brand mark being partly obscured by its glyph and the
theme icon containing non-text characters. Source/browser color checks give
brand text/fill ratios of approximately 6.64:1 light / 9.85:1 dark, and foreground
icons/page ratios above 13:1. Clerk's gradient/branding/icon cases also require
human/assistive-technology review; inconclusive counts are retained in the audit
JSON. Zero reported violations does not certify complete accessibility.

The boundary contrast target follows [W3C non-text contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
The unchanged text palette and prior checks are in [the Phase 7 audit](UX_AUDIT.md).
Clerk's supported secondary-color/font controls are documented in its
[appearance variables reference](https://clerk.com/docs/nextjs/guides/customizing-clerk/appearance-prop/variables).
Installed Next 16.3 image/CSS documentation, Pillow 12.3 source and
[Pillow's image documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html),
and [axe's API documentation](https://www.deque.com/axe/core-documentation/api-documentation/)
were consulted. The requested version-specific Pillow documentation URL was
unavailable; installed source established the version-specific behavior.

## Measured image performance

Baseline: the actual Phase 7 frontend browsing the same fresh seeded database.
Final: the updated production build against the same original media. Measurements
record browser-selected URLs, successful decoding, HTTP image response-body byte
counts, and source loading behavior at **1440px and 390px, DPR 1**. Final control
fetches bypass cache and compare original and selected representation bodies.
This is payload measurement, not a production LCP or network-latency benchmark.
Initial detail navigation followed the gallery and could use cache, so recorded
local timings must not be interpreted as comparable cold-load latency.

| Scenario | Original response bodies | Final selected bodies | Reduction |
| --- | ---: | ---: | ---: |
| Three-photo Explore, desktop | 12,221,965 bytes | 3,864,172 bytes | 68.38% |
| Three-photo Explore, mobile | 12,221,965 bytes | 3,864,172 bytes | 68.38% |
| Sunset details, desktop | 4,451,028 bytes | 166,844 bytes | 96.25% |
| Sunset details, mobile | 4,451,028 bytes | 22,738 bytes | 99.49% |

These final values include the retained color profile. The remaining 3,785,028
city-image bytes dominate gallery delivery because that legacy source exceeds
the bounded decode policy. Original-only fallback is deliberately included in
the gallery total, rather than excluded to improve the headline result.

Representative complete derivative payloads:

| Source | Original | 320px edge | 640px edge | 1280px edge | 1920px edge |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sunset, 3172 × 3172 | 4,451,028 | 10,954 | 22,738 | 166,844 | 811,018 |
| Artwork, 3544 × 4028 | 3,985,909 | 20,842 | 56,406 | 188,216 | 546,430 |

Units are bytes. The artwork's historical `.webp` filename actually contains
JPEG bytes; existing files/metadata were preserved. Portrait widths are
282/563/1126/1689px, not the edge values in the table. New uploads still enforce
MIME/content agreement.

The standalone two-photo generation probe recorded process peak RSS of about
164 MiB and then 201 MiB (cumulative process peaks), including Python/Pillow and
encoder workspace. See [variant benchmark data](phase8/variant-benchmark.json).
This is an observation for these images, **not an RSS limit**. The 16 MP/edge
checks and serialized decoding bound each image job; total request concurrency
and API worker count still need deployment-level resource limits.

Evidence: [baseline browser metrics](phase8/before.json),
[final browser metrics and cold controls](phase8/after.json),
[engine availability](phase8/browsers.json), and
[variant/RSS benchmark](phase8/variant-benchmark.json).
Representative inspected screenshots show [upload labels and controls](phase8/light-owner-upload.jpg),
[the optimized public gallery](phase8/dark-public-explore.jpg),
[keyboard-focused deletion confirmation](phase8/light-owner-delete-dialog.jpg), and
[the existing-image editor](phase8/dark-owner-edit.jpg). Avatars are privacy-masked.

## Browser compatibility

| Engine | Actual result |
| --- | --- |
| Chromium 153.0.8010.52 | Complete 24-test strict suite PASS, zero skipped; real Clerk signup/login/logout, upload/edit/replacement/delete, two-account ownership, public browsing, responsive layouts, theme and keyboard checks. |
| Firefox 157.0, Playwright build 1555 | Matching engine downloaded successfully. Launch BLOCKED before reaching PixShare by unsupported-host/missing shared libraries (including GTK/X11 and libstdc++). Application journeys NOT RUN. |
| WebKit 27.2, Playwright build 2370 | Matching engine downloaded successfully. Launch BLOCKED before reaching PixShare by missing runtime libraries (including GTK4, GStreamer, ICU74). Application journeys NOT RUN. |

Playwright 1.64.1 downloaded its Ubuntu 24.04 fallback engines because the Nix
workstation is unsupported. These are environmental launch failures, not
application test failures. Browser sandboxes/security checks were not disabled.
The project config now keeps Chromium-specific executable options scoped to
Chromium and provides optional Firefox/WebKit public **and authenticated**
projects. Actual cross-engine compatibility remains unverified.

On a supported development/CI host with system dependencies available:

```bash
cd web
pnpm exec playwright install --with-deps firefox webkit
E2E_REQUIRE_AUTH=1 E2E_CROSS_BROWSER=1 pnpm test:e2e
```

This session did not install system packages, publish a CI run, or change the
application infrastructure to work around the host limitation.

## Regression results and commands

| Check | Result |
| --- | --- |
| Backend full suite | PASS — 84 passed in 12.21s; 19 additional cases beyond Phase 7. |
| Ruff 0.16.1 | PASS — all checks passed. |
| basedpyright 1.39.9 | PASS — 0 errors, warnings, notes. |
| Frontend lint and TypeScript | PASS on the final implementation. |
| Production build, Next.js 16.3.0 | PASS on the final implementation; all routes compiled/generated. |
| Complete strict Chromium suite | PASS — 24 passed, zero skipped, 2.8m. |
| Final control-contrast follow-up | PASS — 5 passed, zero skipped, 1.2m: setup plus all public device profiles and owner accessibility/keyboard checks on the final border-corrected build. |
| Firefox/WebKit | BLOCKED at engine launch; no workflow pass claimed. |
| Final diff/privacy/evidence checks | PASS — whitespace checks, local documentation links, inspected masked screenshots, zero temporary non-seed browser posts, and private-key/account-address scans of selected evidence/source/static assets. |

Backend tests cover generation dimensions/aspect/no-upscale, transparency,
orientation and profiles, partial encoding/write failure, original-only fallback,
manifest repair/idempotence, deletion despite an original unlink error, public
cache headers, replacement cleanup, commit failures, committed refresh failure,
legacy compatibility, and exclusive-filename collision preservation. Existing
ownership, signature/origin/expiry, MIME/size/bomb and storage tests remain active.

Commands executed with the isolated stack:

```bash
# Root: TEST_DATABASE_URL points only to disposable pix_share_phase8_test;
# UPLOADS_DIR is /tmp/pixshare-phase8-backend-uploads.
UV_CACHE_DIR=/tmp/pixshare-uv LD_LIBRARY_PATH=/nix/store/2ga5nd1m56n5cx2wh8vbf6nrdhqk2f0q-gcc-15.3.0-lib/lib uv run --no-sync pytest -q --tb=short
/nix/store/znb3q6g1ik34454j3vcjx824h1871asg-glibc-2.42-84/lib/ld-linux-x86-64.so.2 .venv/bin/ruff check .
node .venv/lib/python3.12/site-packages/basedpyright/index.js

# web/, using the pinned pnpm version:
pnpm lint
pnpm typecheck
NEXT_TELEMETRY_DISABLED=1 pnpm build
E2E_REQUIRE_AUTH=1 NEXT_TELEMETRY_DISABLED=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/etc/profiles/per-user/edtosoy/bin/chromium pnpm test:e2e
```

The browser API uses fresh `pix_share_phase8_e2e` and
`/tmp/pixshare-phase8-uploads`. Existing migrations were applied only to the two
fresh Phase 8 databases. User databases, uploads, and persistent Clerk accounts
were preserved. Test registration creates and removes only its random user and
associated onboarding organization; ordinary test posts are removed in `finally`.

Failures encountered were investigated rather than counted as passes: an early
media-subclass import error was fixed; a gated-image test waited for `load` while
holding the eager image request and was corrected to wait for DOM readiness;
native dialog reverse focus was reproduced and repaired; the MIME test fixture
was corrected after the independent dimension limit changed its first rejection;
and an intermediate Clerk color adjustment was made theme-aware. A daemon restart
interrupted one run; its incomplete result was discarded and the restored full
suite passed. No checks were disabled to obtain passing results.

An SDK shutdown diagnostic emitted a token-bearing development URL during
investigation. Test-only redaction now protects those diagnostics. Actual keys,
account addresses, passwords, session tokens, and raw authenticated axe DOM are
not included in this report or selected evidence.

## Reproduction and remaining work

No new Clerk setup is required with the current ignored configuration. The audit
script uses the existing matching development keys and dedicated test account:

```bash
# Start the isolated real API and built frontend, then from web/:
PHASE8_ISOLATED=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/etc/profiles/per-user/edtosoy/bin/chromium node scripts/phase8-audit.mjs after
```

The script writes sanitized payload/axe metrics and masks account avatars in
selected screenshots. It creates and deletes only its own real post. To optimize
existing personal/application uploads later, deliberately configure the correct
database/upload directory and run the documented backfill; it was **not** run on
that data in this session.

Remaining risks:

- Firefox/WebKit workflows, real iOS Safari/Android browsers, assistive technology,
  forced colors, and independent human acceptance remain unverified. Axe and
  keyboard automation are not a WCAG conformance certificate.
- Over-budget legacy, animated, and profiled non-RGB images retain larger original
  delivery. A future isolated worker with a larger resource budget could optimize
  additional formats/sizes; none was added here.
- WebP is lossy. Source profiles/originals are retained, but image quality across
  every photo/profile still needs visual acceptance. Captions can be imperfect
  image descriptions; there is no new dedicated alt-text product field.
- One decode/resize at a time per process trades throughput for bounded raster
  work. Ingress body/rate limits, worker count, and aggregate memory remain
  deployment responsibilities; no load-test or production LCP claim is made.
- Storage and PostgreSQL cannot commit atomically. Crashes/cancellation or cleanup
  errors can leave orphan files; existing manual reconciliation remains necessary.
  Immutable public media can remain in browser caches after server deletion;
  media URLs are not an authorization mechanism.

Final cleanup completed: no temporary non-seed posts remain in the isolated
browser database. Original fixture hashes match their source bytes. Persistent
Clerk accounts and the user's existing databases/uploads were preserved. The
temporary API, frontend and PostgreSQL servers were stopped; test databases,
media and local evidence remain available for inspection. No commit, push, or
deployment was performed.
