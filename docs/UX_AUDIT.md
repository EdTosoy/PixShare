# Phase 7 — UI/UX audit

Recorded 2026-10-23. Reviewed the existing production frontend with Playwright,
the real local FastAPI/PostgreSQL application, and the two configured Clerk
development accounts. Six focused UI fixes preserve the existing design and API
contracts. No dependencies, migrations, authentication bypasses, commits,
pushes, or deployments were added in this phase.

## Coverage and evidence

The six routes were captured before and after the fixes in every cell below:

| Page | Route | Desktop | Tablet | Mobile | Themes |
| --- | --- | --- | --- | --- | --- |
| Landing | `/` | 1440 × 1000 | 768 × 1024 | 390 × 844 | Light, dark |
| Explore | `/explore` | Same | Same | Same | Light, dark |
| Image details | `/posts/{audit-post}` | Same | Same | Same | Light, dark |
| Upload | `/upload` | Same | Same | Same | Light, dark |
| My Gallery | `/me` | Same | Same | Same | Light, dark |
| Editing | `/posts/{audit-post}/edit` | Same | Same | Same | Light, dark |

This is 36 page/layout/theme combinations per pass. Additional captures cover
empty galleries, a successful upload/update, a long caption, its expanded state,
deletion confirmation/failure, a rejected upload, a filtered empty gallery,
loading, and a gallery network error. The main matrix uses an authenticated
owner so private pages and their real actions are visible. The regression suite
also exercises signed-out browsing and protected-page guidance at three device
profiles.

Full-resolution captures and sanitized layout measurements are retained locally
in `web/ux-audit-artifacts/{empty,before,after}/`. The raw artifact directory is
ignored. Representative screenshots, comparison pairs, overview sheets, and
measurements are saved in [ux-audit/](ux-audit/). Overview sheets show all six
pages, light above dark, for each requested width. Account avatars are masked
with a gray square; this is a privacy mask, not a missing UI asset. No account
menus, credentials, JWTs, authenticated traces, or browser storage state were
saved as audit evidence.

Start with the [screenshot index](ux-audit/README.md), or open the
[desktop](ux-audit/overview-desktop.jpg), [tablet](ux-audit/overview-tablet.jpg),
and [mobile](ux-audit/overview-mobile.jpg) overview sheets.

The application data comes from three bundled demo images seeded into a fresh
isolated database plus one real, authenticated upload. Long captions were saved
through the editing form and restored afterward. Network failure/loading states
use aborted or delayed requests; successful requests still reach the real API.
No successful API responses or authentication were mocked. The upload-error
capture uses the bundled `sample_city.png`, whose bytes are actually JPEG: the
real API correctly returns HTTP 400.

## Findings and before/after changes

| Priority | Verified problem and cause | Change and verification |
| --- | --- | --- |
| High | The entire caption became a 26px heading. A roughly 1,900-character caption pushed mobile metadata and owner actions far below the photo. | Captions over 200 characters use a concise heading and native **Read full caption** disclosure with readable body text. Short captions retain the existing presentation. A real 5,000-character upload is preserved byte-for-byte; keyboard Enter expands/collapses it, and collapsed owner actions remain within the first 1,300 document pixels at 390px. |
| Medium | All upload/update errors appended **Sign in**, including a real invalid-image HTTP 400 for an already authenticated owner. | The sign-in link appears only for a typed HTTP 401/session-expiry error. Invalid files retain their preview and an enabled retry action; selecting a valid file clears the error and uploads successfully. |
| Medium | `.delete-dialog p` overrode the shared error color. A failed deletion looked like muted explanatory text in both themes. | A scoped error selector restores the existing error token. Real network failure leaves the dialog and post intact; cancellation restores focus to Delete. Error text remains explicit, so color is not the only signal. |
| Medium | An empty format filter suggested another format, but its primary action sent users to upload. | Filtered empty galleries offer **Clear format filter**, reset pagination, and preserve sort. The regression test restores the owner's actual image through this action. Unfiltered galleries retain **Share an image**. |
| Medium | Light helper text `#657067` on soft background `#eeefe9` measured **4.465:1**, including the landing callout and focused upload picker text. | A small change to the light muted token, `#626d64`, raises that pair to **4.667:1**. A new browser assertion failed on the old production build at 4.465 and passes on the final build. Dark tokens are unchanged. |
| Low | Theme targets measured **34 × 36px** on desktop/tablet and **26 × 36px** on mobile. They were less comfortable than nearby controls. | A non-shrinking **44 × 44px** theme target now matches primary control sizing. All requested layouts still fit. This improves usability; the previous target already exceeded the 24px WCAG minimum. |

Comparison screenshots:

| Scenario | Before | After |
| --- | --- | --- |
| Mobile long caption and owner controls | [Before](ux-audit/before/mobile-light-long-caption.jpg) | [Collapsed](ux-audit/after/mobile-light-long-caption.jpg), [expanded](ux-audit/after/mobile-light-expanded-caption.jpg) |
| Invalid upload recovery | [Before](ux-audit/before/mobile-light-upload-error.jpg) | [After](ux-audit/after/mobile-light-upload-error.jpg) |
| Deletion error, dark theme | [Before](ux-audit/before/mobile-dark-delete-error.jpg) | [After](ux-audit/after/mobile-dark-delete-error.jpg) |
| Filtered empty gallery | [Before](ux-audit/before/mobile-light-filter-empty.jpg) | [After](ux-audit/after/mobile-light-filter-empty.jpg) |
| Landing helper text and theme target | [Before](ux-audit/before/desktop-light-home.jpg) | [After](ux-audit/after/desktop-light-home.jpg) |

Relevant implementation: `PostDetails.tsx`, `PostForm.tsx`, `Gallery.tsx`, and
`app/globals.css`. `e2e/authenticated.spec.ts` adds one real-account mobile UX
regression; `e2e/public.spec.ts` adds contrast and target-size checks to existing
journeys. `scripts/ux-audit.mjs` reproduces the screenshot matrix and state probes.

## Design and interaction assessment

| Area | Observations |
| --- | --- |
| Hierarchy and navigation | One main heading per captured page; clear page introductions, primary upload actions, and active navigation underlines. Mobile navigation wraps into an intentional second row. Existing landing typography and restrained green palette remain coherent. |
| Typography and spacing | Consistent headings, labels, gutters, and form widths across the matrix. Long-caption hierarchy is repaired. Small secondary type and truncated card captions remain opportunities below. |
| Image presentation | Gallery cards crop consistently; detail and editing previews contain the complete image. Images decode successfully during capture. Contained images have visible letterboxing on narrow screens; this preserves the full photograph. |
| Responsiveness | No document-level horizontal overflow in the final 52 captured page/state combinations. Requested widths preserve navigation, filters, form actions, owner controls, and dialogs. Desktop/tablet grids and the single-column mobile grid remain intact. |
| Keyboard and semantics | Existing skip link works. Inputs have labels and help text. The new disclosure is keyboard operable. Native deletion confirmation focuses Keep image, Escape cancels, and focus returns to Delete. Roles expose errors and success feedback. These focused checks do not establish complete screen-reader accessibility. |
| Feedback and recovery | Invalid type/size checks, real server rejection, selected-image preview, update/upload success, destructive confirmation, network failure, retry, and filter reset were exercised. Existing pending controls and reduced-motion styling are retained. |

Inspected states include [empty personal gallery](ux-audit/empty/mobile-dark-gallery-empty.jpg),
[loading](ux-audit/after/mobile-dark-loading.jpg),
[gallery failure](ux-audit/after/mobile-dark-gallery-error.jpg),
[delete confirmation](ux-audit/after/mobile-dark-delete-dialog.jpg), and
[successful upload](ux-audit/before/desktop-light-upload-success.jpg).
Empty landing/Explore/personal-gallery captures were taken before seeding,
without deleting existing application data. Gallery retry was then observed
returning real images after restoring the connection.

Calculated final token contrast ratios:

| Text/background pair | Light | Dark |
| --- | --- | --- |
| Main text/page | 13.72:1 | 14.72:1 |
| Muted/page | 5.13:1 | 7.95:1 |
| Muted/surface | 5.40:1 | 7.03:1 |
| Muted/soft | 4.67:1 | 6.41:1 |
| Error/surface | 6.60:1 | 8.41:1 |
| Primary button text/fill | 6.64:1 | 9.85:1 |

The normal-text threshold is 4.5:1; calculations use browser/source colors rather
than screenshot antialiasing. See [W3C contrast guidance](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html).
The target-size minimum is 24 × 24 CSS pixels with defined exceptions; 44px is
the usability target chosen here. See [W3C target-size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
These sampled checks are not a WCAG conformance claim.

## Ruff findings

All seven findings documented in Phase 6 are addressed; locked Ruff 0.16.1 now
passes across the repository.

| Original finding | Resolution |
| --- | --- |
| I001, `app/api/dependencies.py` | Organize imports. |
| I001, `app/core/upload.py` | Organize imports. |
| Two I001 findings, `tests/api/posts/test_create.py` | Organize imports, including the local helper import. |
| UP017, lifecycle and signed-auth integration tests | Use `datetime.UTC` through the imported `UTC` alias; remove unused timezone imports. |
| BLE001, media cleanup in `app/api/routes/posts.py` | Retain the deliberate broad handler with a local, explained `noqa: BLE001`. A committed write must survive any storage-adapter cleanup failure. Narrowing this handler could incorrectly fail a successful mutation. Sanitized logging is preserved. |

The backend cleanup-failure and committed-replacement regressions pass. No
global lint exclusions or security checks were relaxed.

## Verification results

| Check | Result |
| --- | --- |
| Backend pytest | PASS — 65 passed in 6.18s. |
| Ruff 0.16.1 | PASS — all checks passed. |
| basedpyright 1.39.9 | PASS — 0 errors, warnings, notes. |
| Frontend ESLint | PASS. |
| Frontend TypeScript | PASS. |
| Next.js 16.3.0 production build | PASS — all routes compiled/generated. |
| Strict Playwright suite | PASS — 17 passed, zero skipped, 1.8m, on the final production build. Includes setup, 12 public/device tests, and 4 real-account tests. |
| Final screenshot/state matrix | PASS — 52 final captures, all with one main heading, 44 × 44px theme targets, and no document-level horizontal overflow. |
| Whitespace and evidence privacy review | PASS — final artifacts inspected, local screenshot links checked, no private keys/account addresses found in the scanned report, new test/capture source, or browser static assets. |

Executed check entrypoints, from the repository root unless indicated:

```bash
# TEST_DATABASE_URL targets only the fresh disposable pix_share_phase7_test DB.
# UPLOADS_DIR is /tmp/pixshare-phase7-backend-uploads for this command.
UV_CACHE_DIR=/tmp/pixshare-uv LD_LIBRARY_PATH=/nix/store/2ga5nd1m56n5cx2wh8vbf6nrdhqk2f0q-gcc-15.3.0-lib/lib uv run --no-sync pytest -q --tb=short
/nix/store/znb3q6g1ik34454j3vcjx824h1871asg-glibc-2.42-84/lib/ld-linux-x86-64.so.2 .venv/bin/ruff check .
node .venv/lib/python3.12/site-packages/basedpyright/index.js

# From web/:
node node_modules/eslint/bin/eslint.js .
node node_modules/typescript/bin/tsc --noEmit
NEXT_TELEMETRY_DISABLED=1 node node_modules/next/dist/bin/next build
E2E_REQUIRE_AUTH=1 NEXT_TELEMETRY_DISABLED=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/etc/profiles/per-user/edtosoy/bin/chromium node node_modules/@playwright/test/cli.js test
```

The first backend attempt set `DATABASE_URL` instead of the fixtures'
`TEST_DATABASE_URL`, so all 65 tests errored while connecting to the unused
default port. The corrected run above passes. A separate, intentionally failing
single public browser test reproduced the old contrast defect before rebuilding.
Neither failed run is counted as a pass.

Installed executables were used directly because this workstation's pinned pnpm
download/signature setup was unavailable, as recorded in Phase 6. Nix's ELF
loader/library workarounds above run the existing locked tools. No signature
checks were disabled or dependencies reinstalled. Chromium retained its sandbox.
Installed Next.js CSS and Playwright documentation was consulted, especially
its advice to verify CSS ordering and browser journeys against production builds.

Final cleanup completed: the audit-owned upload was deleted through the real API;
the two configured Clerk accounts were preserved. The temporary API, frontend,
and PostgreSQL processes were stopped. Disposable database/media files and the
local evidence remain available. There are 65 saved JPEGs under `docs/ux-audit/`,
including the 52 final captures, selected baseline/empty states, and three overview
sheets (approximately 4.64 MiB including measurements and the index).

## Reproducing the visual audit

No additional Clerk setup is needed with the current ignored local configuration.
For another workstation:

1. Supply matching Clerk development keys in ignored `.env` and
   `web/.env.local`, and two dedicated verified accounts in ignored
   `web/.env.e2e.local` as `E2E_USER_EMAIL` and `E2E_OTHER_USER_EMAIL`.
   Keep the API authorized-party list consistent with `http://localhost:3000`.
   Never put key values or account addresses in this report or screenshots.
2. Create a fresh PostgreSQL database for browser/audit data and a separate
   disposable database ending in `_test` for pytest. This run used
   `pix_share_phase7_e2e` and `pix_share_phase7_test` on local port 55439.
   Apply the existing Alembic migrations to each; do not point cleanup fixtures
   at a user database. Use separate upload directories; this audit's API uses
   `/tmp/pixshare-phase7-uploads`.
3. Start the real API on port 8000 and the production frontend using
   `node scripts/start.mjs` from `web/`. Start capture with an empty isolated
   database if empty-state evidence is required. Use Node 24 for the capture
   script's native TypeScript helper import.
4. From `web/`, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` if needed, and run:

   ```bash
   UX_AUDIT_ISOLATED=1 node scripts/ux-audit.mjs empty
   # Seed only the isolated API database using: uv run --no-sync python -m scripts.seed_db
   UX_AUDIT_ISOLATED=1 node scripts/ux-audit.mjs before
   # After applying changes, rebuild/restart the frontend before the next capture.
   UX_AUDIT_ISOLATED=1 node scripts/ux-audit.mjs after
   UX_AUDIT_ISOLATED=1 node scripts/ux-audit.mjs cleanup
   ```

The script creates one real owner post, records only its public post ID in the
ignored artifact directory, and removes only that post during cleanup. Dedicated
Clerk users and pre-existing database/media files are preserved. Do not run the
capture script against production or a personal data database. Stop a manually
started frontend before the normal Playwright suite, whose configuration starts
its own server.

## Remaining issues and limits

- Secondary labels are deliberately small: some card format labels are 9px,
  eyebrows 10px, and form hints 11px. Their checked colors meet contrast, but
  increasing their size would improve readability and needs a broader density
  decision. Tablet cards also truncate long captions; complete captions remain
  available on details.
- Image alternative text currently reuses captions or filenames. A 5,000-character
  caption can therefore produce a verbose image/link accessible name even though
  its visual layout is repaired. Dedicated descriptive alt text and screen-reader
  testing remain follow-up work.
- Detail images retain a tall contained frame on mobile, with letterboxing.
  This protects the entire image but uses substantial vertical space. Pagination
  also remains visible in empty/error states. These are lower-priority design
  opportunities, not broken API behavior.
- The seeded PNG/WebP demo filenames and metadata do not match their JPEG bytes.
  This pre-existing fixture limitation was preserved; genuine new uploads remain
  validated and the existing browser test replaces an image with a real PNG.
- This audit is Chromium automation on one workstation, including device-sized
  viewports, keyboard interactions, sampled contrast, and reduced motion. Real
  iOS Safari/Android browsers, Firefox/WebKit, assistive technologies, forced
  colors, browser zoom/text-resizing combinations, large real-user collections,
  image performance on mobile networks, and independent human acceptance were
  not verified. No full accessibility or performance certification is claimed.
