# MVP implementation record

For the subsequent Phase 6 authentication audit, repaired browser suite, current
results, and remaining live-account setup, see [Authentication verification](AUTH_VERIFICATION.md).
The results below are the earlier MVP verification record.

## Audit (2026-10-23)

Existing architecture: FastAPI async routes, SQLAlchemy 2, PostgreSQL, two
Alembic migrations; local Storage implementation; Next.js 16.3 App Router,
React 19, Clerk 7, TanStack Query 5, Tailwind 4, pnpm lockfile.
The existing 50 backend tests pass against a freshly migrated isolated
PostgreSQL 17 database. Initial environment failures were a read-only uv cache
and missing Nix libstdc++ search path, resolved for verification only.

Verified code defects: Compose references nonexistent Dockerfile (the file is
lowercase dockerfile), omits web; create has no upload rollback cleanup;
delete removes media before commit; replacement catches refresh failures after
commit and can delete referenced media; ordering lacks a tie-breaker; local
storage trusts filename extensions and deletes by basename of arbitrary URLs;
upload validation reads the entire file and does not handle decompression bombs;
SQL debug logging exposes parameter values; seed paths only work in containers.
Frontend calls public posts “Your posts”, promises GIF support the API rejects,
has no preview/filter/pagination/personal gallery, no cache invalidation on
create, and lacks focus trapping in its confirmation dialog. Architecture docs
claim an S3 implementation that does not exist.

## Decisions

- Preserve routes, response arrays, models, data, migrations, Clerk authentication,
  and the existing storage interface. Add /users/me/posts with identical filters.
- Keep a modular monolith; shared UI controls and typed API functions suffice.
- Commit database changes before removing old media. Clean newly uploaded media
  only on commit failure; a refresh failure after commit must preserve it.
  Serialize owner writes with row locks. Log storage cleanup failure without
  leaking URLs/SQL/secrets; failed cleanup can leave orphans for reconciliation.
- Canonical storage extensions, bounded validation, configurable CORS and media
  paths. Local disk remains the free default; document the S3 adapter contract
  and operational decisions without adding unneeded SDK/infrastructure.
- Gallery design: warm neutral canvas, generous image grid, crisp type, subtle
  borders, muted green actions; system-aware light/dark theme with manual toggle.
  No remote font fetches, animation library, or external demo-image dependency.
- Public browsing works without Clerk keys; authenticated actions show explicit
  configuration/sign-in states. No development authentication bypass.
- Tests use isolated PostgreSQL and real HTTP data. Live Clerk browser journeys
  require dedicated test-instance credentials; missing credentials are reported,
  never replaced with mocked production authentication.

## Framework evidence

Read installed Next.js 16.3.0 documentation before implementation:
web/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/{page,proxy}.md,
02-components/image.md, and 01-app/02-guides/testing/playwright.md.
Pages use async server params or client useParams; proxy remains proxy.ts.
Use unoptimized next/image for browser-direct API media so Docker does not need
server-side access to browser localhost and no private-IP optimizer allowance.


## Verification results

Local verification uses freshly migrated PostgreSQL 17.11 databases on an
isolated port (55439), disposable media, and system Chromium with its sandbox
enabled. Nix required a libstdc++ library-path override for Python wheels and
writable uv/pnpm caches under /tmp. Repository checks were not weakened.

| Check | Result | Evidence / scope |
| --- | --- | --- |
| Baseline backend `uv run pytest -q` | PASS | 50 existing tests, isolated PostgreSQL |
| New lifecycle cases before fixes | FAIL (expected reproduction) | All four failed: create cleanup, delete rollback, replacement refresh, tied timestamp ordering |
| Final backend `uv run pytest -q` | PASS | 65 tests; original tests preserved; failure regressions, MIME/format validation, real Clerk SDK signatures and full HTTP CRUD/ownership |
| `ruff check .` | PASS | Native installed Ruff used on Nix; same repository configuration |
| `basedpyright` | PASS | 0 errors, 0 warnings |
| Frontend ESLint / TypeScript | PASS | `web/node_modules/.bin/eslint .` and `tsc --noEmit`, equivalent to package scripts |
| Baseline `next build` | FAIL | Google Fonts network fetch unavailable |
| Final `next build` | PASS | Standalone output and all requested routes; no remote font requirement |
| `docker compose config --quiet` | PASS | Correct file paths, services and interpolation |
| `docker compose build` | PASS | Both API and web images built, including locked dependency install and Next production build |
| Isolated Compose startup | PASS | Fresh project pixshare-mvp-check on ports 13000/18000/55440; migrations and healthy PostgreSQL/API; nonroot seed/media writes |
| Local standalone Playwright | PASS | 12 public checks across desktop, tablet and mobile; 2 auth-related skips |
| Docker-stack Playwright | PASS | 12 public checks against the containerized Next/API/PostgreSQL stack; 2 auth-related skips |
| Live Clerk browser setup and CRUD | SKIPPED | No matching development-instance keys or two dedicated test accounts available |

The backend JWT integration uses ephemeral RSA test keys with the actual Clerk
SDK, signature/time/origin validation, real HTTP requests and PostgreSQL.
It does not override authentication or prove hosted Clerk sign-in, JWKS fetch,
Clerk's UI, or authenticated browser interactions. The existing endpoint tests
also retain their dependency-override fixtures for targeted failure injection.

Inspected local browser evidence: desktop and mobile home, desktop/tablet dark-mode
galleries, and image details. Browser artifacts are in ignored web/test-results/.
Tests observe image decode, routing, actual API data/filtering, responsive
widths, theme persistence, reduced-motion preference, keyboard skip-link focus,
and rejection of unsigned API mutations. They do not establish full WCAG
conformance. The conditional Clerk journey covers upload validation, preview,
caption edit, replacement, another user's API rejection and dialog focus/deletion
when its prerequisites are configured.

Public browser CI now starts PostgreSQL and the real API, seeds only that test
database, and runs Playwright after lint/typecheck/build. Hosted CI itself has
not been run from this workspace; no commits or pushes were made.

The disposable Docker preview is left running at http://localhost:13000
(API http://localhost:18000). It contains only bundled demo data. Stop this
specific test project without deleting volumes with:

```bash
docker compose --env-file .env.example -f /tmp/pixshare-verify-compose.yaml -p pixshare-mvp-check stop
```

The separate native API/PostgreSQL test processes were stopped after verification.
The standard ports remain available for the documented local startup.

## Remaining limitations

- Authenticated browser journey is implemented but unverified with live Clerk.
- Original images are delivered directly; no thumbnail/CDN transformation yet.
- S3 is investigated/documented, not implemented or verified against a vendor.
- Storage cleanup is best-effort after commit; crash/orphan reconciliation is
  manual. No distributed transaction or create-idempotency contract.
- Full accessibility audit, moderation/privacy policies, ingress rate/body
  limits, production readiness checks and monitoring need deployment-specific
  decisions. No deployment or paid provisioning was performed.
- Existing .envrc user modification was present at audit and was not edited.

## Changed-file inventory

All task changes are uncommitted. The pre-existing .envrc change is excluded.

- `.dockerignore`
- `.env.example`
- `.github/workflows/web-ci.yaml`
- `AGENTS.md`
- `README.md`
- `app/api/dependencies.py`
- `app/api/routes/auth.py`
- `app/api/routes/posts.py`
- `app/api/routes/users.py`
- `app/core/config.py`
- `app/core/upload.py`
- `app/db/session.py`
- `app/main.py`
- `app/storage/dependencies.py`
- `app/storage/local.py`
- `docker-compose.yaml`
- `dockerfile`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION.md`
- `docs/PRODUCTION.md`
- `scripts/seed_db.py`
- `tests/api/posts/test_create.py`
- `tests/api/posts/test_lifecycle.py`
- `tests/conftest.py`
- `tests/test_auth_integration.py`
- `tests/test_storage.py`
- `web/.dockerignore`
- `web/.env.example`
- `web/.gitignore`
- `web/AGENTS.md`
- `web/Dockerfile`
- `web/README.md`
- `web/app/explore/page.tsx`
- `web/app/globals.css`
- `web/app/layout.tsx`
- `web/app/me/page.tsx`
- `web/app/page.tsx`
- `web/app/posts/[id]/edit/page.tsx`
- `web/app/posts/[id]/page.tsx`
- `web/app/posts/new/page.tsx`
- `web/app/posts/page.tsx`
- `web/app/providers.tsx`
- `web/app/sign-in/[[...sign-in]]/page.tsx`
- `web/app/upload/page.tsx`
- `web/components/Feedback.tsx`
- `web/components/Gallery.tsx`
- `web/components/Navigation.tsx`
- `web/components/PersonalGallery.tsx`
- `web/components/posts/DeletePostDialog.tsx`
- `web/components/posts/EditPost.tsx`
- `web/components/posts/ImagePicker.tsx`
- `web/components/posts/PostCard.tsx`
- `web/components/posts/PostDetails.tsx`
- `web/components/posts/PostForm.tsx`
- `web/components/posts/PostView.tsx`
- `web/e2e/authenticated.spec.ts`
- `web/e2e/global.setup.ts`
- `web/e2e/public.spec.ts`
- `web/lib/api.ts`
- `web/lib/posts.ts`
- `web/lib/users.ts`
- `web/next.config.ts`
- `web/package.json`
- `web/playwright.config.ts`
- `web/pnpm-lock.yaml`
- `web/proxy.ts`
- `web/scripts/start.mjs`
