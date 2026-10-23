# PixShare

A photography-focused image-sharing MVP built on FastAPI, PostgreSQL,
SQLAlchemy/Alembic, and Next.js 16.3 with Clerk, TanStack Query, and Tailwind 4.
Existing migrations and API response contracts are preserved.

## Run the whole application

Prerequisites: Docker Engine and Docker Compose.

```bash
cp .env.example .env
# Edit .env with your Clerk development-instance keys (see below).
docker compose up --build
# Optional: add the three bundled sample images.
docker compose exec api uv run --no-sync python -m scripts.seed_db
```

Open **http://localhost:3000**. API docs: http://localhost:8000/docs.
Compose starts PostgreSQL, applies Alembic migrations, starts the API, then the
frontend. Database and uploads use persistent named volumes. Services bind to
loopback for local use. Do not delete volumes to update the app.

Public browsing works with empty Clerk keys; sharing requires authentication.
Configure these values from the **same Clerk instance**:

- `CLERK_SECRET_KEY`: backend verification and Next.js Clerk proxy; server-only.
- `CLERK_PUBLISHABLE_KEY`: retained backend setting / optional browser-test alias;
  backend session verification uses the secret key or optional JWT public key.
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: frontend publishable key.
- `CLERK_AUTHORIZED_PARTIES=http://localhost:3000`: accepted token origins.
- Optional `CLERK_JWT_KEY`: PEM public verification key; leave blank to use JWKS.

Enable the sign-in methods you want in your Clerk development dashboard.
`/sign-in` uses Clerk's real UI and links to `/sign-up` for account creation. A Clerk account is
mapped to a local User on its first authenticated API request. A seeded demo
user cannot be used to sign in. No development authentication bypass exists.

`NEXT_PUBLIC_*` values are compiled into the frontend; rebuild after changing
keys or the API origin. Never put secret keys in a `NEXT_PUBLIC_*` variable.
Use `localhost` consistently: switching to `127.0.0.1` changes the allowed origin.

## Local development without application containers

Prerequisites: Python 3.12+, uv, Node 24+, pnpm 11.11.0, and PostgreSQL 17.
Use the checked-in lockfiles.

```bash
cp .env.example .env
cp web/.env.example web/.env.local
# Configure matching Clerk keys in both files; web also needs CLERK_SECRET_KEY.
docker compose up -d postgres
uv sync --locked
uv run alembic upgrade head
uv run python -m scripts.seed_db  # optional; works locally and in containers
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd web
pnpm install --frozen-lockfile
pnpm dev
```

For production-mode local frontend verification: `pnpm build && pnpm start`.
The start script copies static assets into Next's standalone output and runs its
server. No Google Fonts fetch is needed to build.

## Application routes

| Route | Behavior |
| --- | --- |
| `/` | Landing page with the six latest public images |
| `/explore` | Public gallery; format filter, newest/oldest sort, 12-image pages |
| `/posts/[id]` | Public image detail; owner controls when signed in |
| `/upload` | Authenticated drag/drop or file-picker upload, preview and caption |
| `/me` | Authenticated personal gallery with the same filters and pagination |
| `/posts/[id]/edit` | Owner-only caption editing, clearing, and image replacement |
| `/sign-in` | Clerk authentication, or configuration guidance when keys are absent |
| `/sign-up` | Clerk registration and required account onboarding |

Legacy `/posts` and `/posts/new` redirect to `/explore` and `/upload`.
Light/dark themes follow the system until explicitly changed. Forms have visible
focus states; the native confirmation dialog traps focus, supports Escape, and
returns focus to its trigger. Reduced-motion preferences disable animation.
Images use responsive API-generated WebP variants inside `picture` with
`next/image` original fallbacks. Gallery images load lazily; details load eagerly.
Originals remain available at their existing URLs. See [image delivery and API
metadata](docs/IMAGE_DELIVERY.md) for limits, cleanup, and optional legacy backfill.

## API

| Endpoint | Access / contract |
| --- | --- |
| `GET /posts` | Public array of posts |
| `GET /posts/{id}` | Public post or 404 |
| `POST /posts` | Bearer-authenticated multipart `file`, optional `caption`; 201 |
| `PATCH /posts/{id}` | Owner-only multipart `file` and/or `caption`; 200 |
| `DELETE /posts/{id}` | Owner-only; returns deleted post; 200 |
| `GET /users/me` | Bearer-authenticated local user ID |
| `GET /users/me/posts` | Bearer-authenticated user's posts only |
| `GET /health` | Process liveness; does not test database readiness |

Both list endpoints accept `limit` (1–100, default 20), `offset` (default 0),
`file_type` (MIME string), and `sort` (`newest` or `oldest`). Ordering uses
`created_at` and UUID as a stable tie-breaker. Offset pages can shift when other
users add/delete posts. Existing list responses remain arrays.

Uploads accept **JPEG, PNG, WebP, at most 10 MiB, 16 megapixels, and 20,000 pixels
per side** (MiB is shown as “MB” in the UI).
The server verifies MIME/format agreement and decodes the image with Pillow;
corrupt images and decompression bombs are rejected before unbounded decoding.
Validation and resizing run off the API event loop with a shared per-process
decode budget. Captions allow 5000
characters. Omitting `caption` preserves it on PATCH; sending `caption=""`
clears it. Post responses add nullable `image` metadata (dimensions and WebP
variants); `url` still points to the original. Legacy records require no migration.
Unknown formats, bad images, and oversized files/dimensions return 400;
authentication/ownership failures return 401/403; invalid request values return
422. The UI presents these errors and refreshes affected queries after writes.

Files use unique names and canonical extensions. Failed database commits clean
new uploads; replacement and deletion remove old media only after commit.
Concurrent owner writes are serialized with PostgreSQL row locks. If physical
cleanup fails after commit, the API logs a sanitized reconciliation warning and
keeps the successful database operation. See the operational limitations below.

## Tests

Backend tests delete all rows in their database. Use a **disposable** database
whose name ends in `_test`, never the application database.

```bash
docker compose up -d postgres
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

For Playwright, start the API against a **separate disposable E2E database**:

```bash
# From the repository root, using the local PostgreSQL service above:
docker compose exec postgres createdb -U postgres pix_share_e2e
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pix_share_e2e uv run alembic upgrade head
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pix_share_e2e UPLOADS_DIR=/tmp/pixshare-e2e-uploads uv run python -m scripts.seed_db
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pix_share_e2e UPLOADS_DIR=/tmp/pixshare-e2e-uploads uv run uvicorn app.main:app --port 8000
```

In another terminal, run `cd web && pnpm exec playwright install chromium`, then
`pnpm test:e2e`. The suite starts the built frontend on port 3000. Stop an
existing development server first, or set `E2E_BASE_URL` to an already-running
test frontend. `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` can select system Chromium;
Chromium's sandbox stays enabled. Screenshots/traces stay in ignored
`web/test-results/`. Public tests use real API/PostgreSQL data on desktop,
tablet, and mobile.

The suite also runs axe-core and keyboard checks in both themes and verifies
responsive variant selection and original fallback. To enable the additional
Firefox/WebKit public and authenticated projects, install their matching engines
and run on a supported host with their system libraries:

```bash
pnpm exec playwright install firefox webkit
E2E_REQUIRE_AUTH=1 E2E_CROSS_BROWSER=1 pnpm test:e2e
```

See [Phase 8 results](docs/PHASE_8_REPORT.md) for actual browser availability,
accessibility scope, performance measurements, and remaining risks.

For hosted Clerk verification, follow the exact [Phase 6 setup and verification
record](docs/AUTH_VERIFICATION.md). Playwright loads ignored `web/.env.local`
and `web/.env.e2e.local`; it needs matching development keys and two distinct
dedicated `+clerk_test` accounts. The form tests use email-code authentication;
the CRUD test uses official Clerk helpers and genuine sessions verified by the
API. The sign-up test creates and cleans up only its own randomly named Clerk
development user. Persistent test accounts are preserved.

```bash
cd web
pnpm build  # rebuild after configuring the frontend publishable key
E2E_REQUIRE_AUTH=1 pnpm test:e2e --project=auth
pnpm test:e2e
```

Without credentials the default suite explicitly skips Clerk setup and five
authenticated journeys. `E2E_REQUIRE_AUTH=1` fails immediately instead. Never
use production credentials or an application database for these tests.

See [verification results and changed-file inventory](docs/IMPLEMENTATION.md)
for this implementation's executed checks and unverified journeys.

## Deployment considerations

This is a production-minded MVP, not a deployed/operated service. See
[architecture](docs/ARCHITECTURE.md) and [production-readiness review](docs/PRODUCTION.md).

- Keep PostgreSQL and Alembic. Back up data and uploads; run migrations once
  before application rollout. Compose auto-migration is a local convenience.
- Configure explicit CORS and Clerk authorized origins, HTTPS, and secrets via
  the deployment environment. Defaults and Compose database credentials are local.
- Local media requires persistent shared storage for multiple API replicas.
  Storage stays behind `app/storage/base.py`; S3-compatible storage has been
  investigated and is documented, but no adapter or cloud resources are installed.
- Filesystem/object-store writes cannot be atomic with PostgreSQL. A crash after
  upload or a failed cleanup can leave orphan files; reconciliation is currently
  manual. A committed write followed by a refresh failure can return 500 even
  though the write succeeded. No idempotency/retry token is implemented.
- Configure request-body limits, rate limits, and monitoring at ingress before
  public deployment. Review image metadata/privacy, moderation, and abuse handling
  for the intended audience.

No deployments, paid infrastructure, commits, pushes, or pull requests are part
of this implementation.
