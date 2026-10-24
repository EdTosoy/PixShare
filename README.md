# PixShare

[![Backend CI](https://github.com/EdTosoy/PixShare/actions/workflows/ci.yaml/badge.svg)](https://github.com/EdTosoy/PixShare/actions/workflows/ci.yaml)
[![Web CI](https://github.com/EdTosoy/PixShare/actions/workflows/web-ci.yaml/badge.svg)](https://github.com/EdTosoy/PixShare/actions/workflows/web-ci.yaml)

A simple online photo album built with **Next.js, FastAPI and
PostgreSQL**. Public browsing, genuine Clerk sign-in, owner-only image CRUD,
responsive WebP variants, and interchangeable local/S3-compatible media storage.

This is a focused full-stack engineering project, with a finished Atelier
interface and tested local workflows. **No public live demo has been deployed.**
Cloud templates are preparation material, not evidence of a running service.

![PixShare desktop, actual local production build](docs/release/desktop-home-light.jpg)

[Mobile gallery](docs/release/mobile-explore-light.jpg) ·
[Light/dark before-and-after screenshots](docs/release/SCREENSHOTS.md) ·
[Release verification](docs/FINAL_RELEASE.md) ·
[Portfolio case study](docs/PORTFOLIO_CASE_STUDY.md)

## What it does

- Browse real photographs without signing in; filter JPEG/PNG/WebP, sort and paginate.
- Sign in with Clerk to upload, edit captions, replace images and delete your posts.
- Preserve composition in proportionate image rows, with a single-column mobile gallery.
- Serve browser-selected WebP variants while retaining original image fallback.
- Support light/dark themes, visible keyboard focus, native confirmation dialogs,
  reduced motion, and explicit loading, empty, success, error and retry states.

There are no feeds, follows, likes, comments, recommendation engines or private
photo vaults. Media URLs are public locations; backend ownership checks protect
mutations, not image reads.

## Architecture

```mermaid
flowchart LR
  Browser[Browser / Next.js] -->|Public reads| API[FastAPI]
  Browser -->|Sign in| Clerk[Clerk]
  Clerk -->|Session token| Browser
  Browser -->|Bearer-authenticated mutations| API
  API -->|Verify session and ownership| Clerk
  API --> DB[(PostgreSQL / SQLAlchemy)]
  API --> Storage[Storage interface]
  Storage --> Local[Local filesystem]
  Storage --> S3[S3-compatible objects]
  Browser -->|Responsive image GET| Local
  Browser -->|Responsive image GET| S3
```

Next.js 16.4.1 / React 19 / TypeScript / TanStack Query / Tailwind 4 provide the
frontend. FastAPI, SQLAlchemy asyncio, Alembic and PostgreSQL implement the API
and persistence. Pillow generates bounded responsive media; boto3 supplies the
optional object-storage adapter. Pytest, Ruff, basedpyright, Playwright and
axe-core provide verification. Docker Compose runs the local application.

See [architecture and transaction boundaries](docs/ARCHITECTURE.md),
[image delivery](docs/IMAGE_DELIVERY.md), and the
[design specification](design.md).

## Run locally with Docker

Prerequisites: Docker Engine and Docker Compose. Local storage is the default;
no cloud account or paid resource is required.

```bash
cp .env.example .env
# Optional: configure matching Clerk development keys in .env for sign-in.
docker compose up --build
# In another terminal, add the bundled demonstration photographs:
docker compose exec api uv run --no-sync python -m scripts.seed_db
```

Open **http://localhost:3000**. API documentation: **http://localhost:8000/docs**.
Compose starts PostgreSQL, applies existing migrations, then starts the API and
frontend. Data and uploads use persistent named volumes; do not delete volumes
when updating. All local service ports bind to loopback.

Public browsing works with empty Clerk keys. To enable sharing, set these from
**the same Clerk development instance**:

- `CLERK_SECRET_KEY`: server-only API verification and Next.js proxy.
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: browser integration.
- `CLERK_PUBLISHABLE_KEY`: optional backend/testing alias for that publishable key.
- `CLERK_AUTHORIZED_PARTIES=http://localhost:3000` and matching `CORS_ORIGINS`.
- Optional `CLERK_JWT_KEY`: verification public key; otherwise the SDK uses JWKS.

Use `localhost` consistently. Enable the desired sign-in methods in Clerk.
`/sign-in` and `/sign-up` use its real UI; a local User is created on the first
verified authenticated API request. The seeded demo user cannot sign in, and
there is no development authentication bypass. Browser-visible `NEXT_PUBLIC_*`
values are compiled in: rebuild the frontend after changing them. Never put a
secret key in a `NEXT_PUBLIC_*` variable or commit a working environment file.

The seed command is idempotent. Newly copied demo photos are bounded to 1920px
and encoded to their declared format; existing stored images are preserved.
Original repository demo files are not rewritten. Actual user uploads retain
original bytes, subject to the validation limits below.

## Run without application containers

Prerequisites: Python 3.12+, uv, Node 24+, pnpm 11.11.0 and PostgreSQL 17.
Keep the checked-in uv and pnpm lockfiles.

```bash
cp .env.example .env
cp web/.env.example web/.env.local
# Configure matching Clerk development keys in both files if using sign-in.
docker compose up -d postgres
uv sync --locked
uv run alembic upgrade head
uv run python -m scripts.seed_db
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd web
pnpm install --frozen-lockfile
pnpm dev
```

For a production-mode local frontend, use `pnpm build` followed by `pnpm start`.
The start script includes Next's standalone static/public assets. Builds do not fetch fonts. Hanken Grotesk is self-hosted; Sentient is served
through Fontshare with a Georgia fallback. See the [font notices](web/public/fonts/atelier/README.md).

## Routes and API

| UI route | Purpose |
| --- | --- |
| `/`, `/explore`, `/posts/[id]` | Public landing, gallery and image detail |
| `/upload`, `/me`, `/posts/[id]/edit` | Authenticated upload, personal gallery and owner editing |
| `/sign-in`, `/sign-up` | Real Clerk authentication or missing-configuration guidance |
| `/posts`, `/posts/new` | Legacy redirects to Explore and upload |

| API endpoint | Access |
| --- | --- |
| `GET /posts`, `GET /posts/{id}` | Public |
| `POST /posts` | Authenticated multipart image, optional caption |
| `PATCH /posts/{id}`, `DELETE /posts/{id}` | Authenticated owner only |
| `GET /users/me`, `GET /users/me/posts` | Authenticated identity/current user's images |
| `GET /health`, `GET /ready` | Process liveness and bounded database/table readiness |

List endpoints retain array responses and accept `limit` (1–100), `offset`,
`file_type` and `sort=newest|oldest`. Ordering uses creation time and UUID as a
stable tie-breaker. The UI uses 12-image pages and a lookahead item; it does not
invent a total count. Concurrent inserts/deletions can shift offset pages.

Uploads accept JPEG, PNG and WebP, **10 MiB maximum, 16 megapixels, 20,000 pixels
per side**. The UI calls MiB “MB.” The API verifies MIME/decoded format agreement
and actual image content before writing. The request envelope has an independent
11 MiB limit. Captions allow 5,000 characters; omitted PATCH captions are retained,
and an explicit empty string clears them.

## Engineering decisions

- **Authorization lives in the API.** Clerk verifies Bearer sessions; the backend
  resolves the user and checks ownership. Hiding UI controls is not authorization.
- **Concurrent writes lock the row.** Replacement/deletion preserve PostgreSQL
  row locking. New media is cleaned on failed commit; old media is deleted only
  after a successful commit. A later refresh failure never deletes committed media.
- **Storage stays replaceable.** Local development needs no S3. New S3 writes use
  immutable groups and private metadata manifests; old local references keep working.
- **Images are browser-direct.** Responsive actual-width WebP source sets use
  320/640/1280/1920px maximum edges, lazy gallery loading and original fallback.
  Variant failure never invalidates an otherwise valid original upload.
- **Operational safeguards are bounded.** Requests have size, receipt-time and
  per-peer limits. Readiness checks have a deadline. Logs avoid private settings,
  SQL parameters, tokens and SDK error bodies.

## Verification

Backend fixtures **delete rows**. Run pytest only against a disposable database
whose name ends in `_test`, never the application database:

```bash
docker compose exec postgres createdb -U postgres pix_share_test
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pix_share_test uv run alembic upgrade head
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pix_share_test uv run pytest -q
uv run ruff check .
uv run basedpyright
cd web
pnpm lint
pnpm typecheck
pnpm build
```

Browser tests need a separate migrated/seeded E2E database and API. Follow
[the isolated setup](docs/AUTH_VERIFICATION.md) and [final verification record](docs/FINAL_RELEASE.md).
Then run `pnpm test:e2e`. Chromium stays sandboxed. Set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to use a compatible installed Chromium.
`E2E_BASE_URL` selects an already-running test frontend; otherwise the suite
starts the built frontend itself.

The full authenticated suite requires matching Clerk development keys and two
separate dedicated `+clerk_test` accounts in ignored `web/.env.e2e.local`.
`E2E_REQUIRE_AUTH=1 pnpm test:e2e` fails if required configuration is missing;
without it, missing authentication tests are explicitly skipped. No production
credentials or normal accounts should be used. Authenticated traces are disabled.

Real S3-compatible tests require the explicit local MinIO fixture and a dedicated
`*-test` bucket. See [S3 setup and limits](docs/PHASE_9_REPORT.md). With
`S3_INTEGRATION_TEST=1` and the ignored local fixture environment configured,
the final local backend run passed all **141 tests**, including those real HTTP
integrations. The default GitHub backend job does not provision MinIO and marks
those opt-in cases as skipped. This distinction is documented, not hidden.

## Scope and limitations

This is a portfolio application with local integration evidence, not a claim of
production operation, scale, compliance or a public live demo.

- PostgreSQL and object storage cannot share one atomic transaction. Crashes or
  failed cleanup can leave orphans; reconciliation is operator-invoked and dry-run
  by default. No idempotency token or automatic orphan-deletion job is implemented.
- Public media retains original metadata. Private sharing, moderation, metadata
  stripping, takedown, account deletion and retention policies are not product features.
- Request limits are per process; shared ingress abuse protection and monitoring
  are deployment concerns. Public cached media can remain readable after deletion.
- Local media needs persistent shared storage for multiple API replicas. Real AWS
  IAM/OIDC/CDN, provider recovery, load and physical-device behavior need their
  own deployment verification. MinIO results do not establish AWS policy correctness.
- Accessibility combines axe, keyboard and contrast checks; it is not a complete
  screen-reader or WCAG conformance certification.

[Production considerations](docs/PRODUCTION.md), [release checklist](docs/RELEASE_CHECKLIST.md)
and [deployment runbook](docs/DEPLOYMENT_RUNBOOK.md) describe the remaining
operational work. Deployment templates are inert examples. No cloud infrastructure
was provisioned or deployed for this release.
