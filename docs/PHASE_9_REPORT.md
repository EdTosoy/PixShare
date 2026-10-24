# Phase 9 — Production-ready media storage

Implemented locally on 2026-10-23. No AWS resources, paid services, deployment,
commit, push, schema migration, legacy backfill or existing-data migration was
performed. Existing application databases, uploaded images and dedicated Clerk
accounts were preserved. Tests use separate Phase 9 databases and media paths.

## Architecture and decisions

`MediaStorage` selects **new writes** using `STORAGE_PROVIDER=local|s3`, default
`local`. It routes reads and deletion by the stored reference, so local legacy
posts continue working when new uploads use S3. Keep both the original local
volume and S3 configuration when switching providers. A single configured S3
bucket/prefix is supported; changing either requires a separately planned
migration. Changing only the public/CDN base does not rewrite database records.

`Storage.upload()` returns a durable reference. Local records retain `/uploads/`
URLs; new S3 records store `s3://bucket/prefix/<random-group>/original.ext` in the
existing `Post.url` column. API serialization resolves the original and variants
to public HTTP(S) URLs. API consumers never receive internal S3 references or
credentials. Existing HTTP contracts, migrations, authentication, ownership
checks, row locks and UI design remain intact.

Each S3 group contains the original, bounded WebP variants and a private
`manifest.json`. Original bytes are preserved. Original MIME type is validated
by the existing upload validation; variants use `image/webp`. Unique groups and
conditional `If-None-Match: *` writes prevent replacement of an existing
original. Initialization and runtime SDK failures use safe errors without raw
provider diagnostics. An operation marker permits cleanup after an ambiguous original PUT
only when a HEAD proves that this request created the object.

The existing Pillow pipeline still enforces 10 MiB, 16 MP and 20,000px-side
limits, decompression-bomb protections, one raster worker per process, aspect
ratios, orientation and alpha handling. S3 work runs in worker threads; local
private temporary files are removed after generation/upload. No queue, external
image processor or new infrastructure is needed for normal local operation.

The manifest is uploaded last. Successful reads fetch only a bounded 16 KiB
manifest, validate its namespace and resolve variant keys to the configured
public base. They never decode images or regenerate variants. Missing, malformed
or inaccessible metadata falls back to the original. The S3 adapter does not
HEAD every variant on every API read; browser fallback handles a derivative
removed externally. Images have immutable keys and one-year public cache
headers; the private manifest is `no-store`.

Runtime boto3 1.43.118 and its locked dependencies provide SigV4 and established
S3 retries. Development-only S3 stubs allow static checking. Existing dependency
versions and the pnpm lockfile were preserved.

## Server configuration

The complete empty-key template is in [`.env.example`](../.env.example).
Configure the **API only**, never `NEXT_PUBLIC_*` variables:

| Variable | Meaning / default |
| --- | --- |
| `STORAGE_PROVIDER` | `local` (default) or `s3` for new writes |
| `UPLOADS_DIR` | Preserve the existing local volume for legacy posts |
| `S3_BUCKET` | Required for S3; also retain when switching new writes back to local |
| `S3_PREFIX` | Safe nonempty namespace, default `pixshare/media` |
| `S3_REGION` | Default `us-east-1` |
| `S3_ENDPOINT_URL` | Empty for AWS; explicit endpoint for compatible services |
| `S3_PUBLIC_BASE_URL` | Public image/CDN root, including bucket path for path-style service URLs |
| `S3_ADDRESSING_STYLE` | `auto` default; `path` for the local test service; `virtual` if required |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Optional paired server secrets; otherwise standard AWS credential chain / IAM role |
| `S3_SESSION_TOKEN` | Optional temporary-credential token |
| `S3_CONNECT_TIMEOUT`, `S3_READ_TIMEOUT` | 3 / 10 seconds per SDK attempt, configurable up to 60 |
| `S3_MAX_ATTEMPTS` | 3 total attempts, bounded to 1–5, standard SDK retry mode |

Production configuration requires HTTPS for the endpoint and public base.
URLs cannot include embedded credentials, query strings, fragments or traversal.
Endpoint override settings from the generic SDK environment are ignored in favor
of this explicit configuration. Do not log settings, raw SDK exceptions or
rendered Compose environments; they can contain secrets.

For AWS, use a server IAM role with namespace-scoped `s3:GetObject`,
`s3:PutObject`, `s3:DeleteObject` and bucket `s3:ListBucket` constrained by prefix.
No runtime bucket creation, ACL modification or policy administration is needed.
Configure the bucket and its public read path before enabling uploads. Prefer
private S3 behind a public CDN with origin access control; alternatively scope
anonymous GET to original/variant paths only. Keep manifest reads and all
listing/writes/deletes private. Do not disable global bucket protections as an
application workaround. No AWS account or keys are needed for local development.

## Isolated local S3 integration

`docker-compose.s3-test.yaml` is opt-in and separate from the default filesystem
stack. It binds only `127.0.0.1:59000`, uses its own named volume and runs the
storage process as a nonroot user. The default application Compose stack does
not start or depend on MinIO.

Community MinIO is now archived and source-only. Public prebuilt image attempts
were rejected by the registries, so `dev/minio/Dockerfile` builds upstream source
at immutable commit `07c3a429bfed433e49018cb0f78a52145d4bedeb` (release
`RELEASE.2025-09-07T16-13-09Z`). **This is an isolated compatibility fixture,
not a production recommendation.** Building requires network access and Go build
time. Evaluate a maintained vendor/service before production deployment.

This session already retained its private local test configuration in the ignored
root `.env.s3-test` (mode 0600). Reuse it; do not run the exclusive-create example
below over an existing file. It points to the dedicated Phase 9 databases on the
local test PostgreSQL server at port 55439 and the isolated MinIO service at
59000. Those are test fixtures, separate from the application's original data.
The MinIO named volume is retained. Root `.env` and web Clerk configuration were
not changed. Verification API/frontend processes were stopped at completion;
the local PostgreSQL and isolated MinIO test services remain available on their
loopback test ports. No production service was started.

For a fresh fixture, reproduce without printing credentials:

1. Install locked dependencies with `uv sync --locked` and `cd web && pnpm install --frozen-lockfile`.
2. Create an ignored, private `.env.s3-test` in the repository root. Generate
   dedicated random local-only credentials into the file; do not paste real AWS
   or Clerk secrets into commands or documentation:

   ```bash
   python - <<'PY'
   import os, secrets
   values = {
       'DATABASE_URL': 'postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/pixshare_s3_browser',
       'UPLOADS_DIR': '/tmp/pixshare-s3-browser-uploads',
       'STORAGE_PROVIDER': 's3',
       'S3_BUCKET': 'pixshare-media-test',
       'S3_PREFIX': 'phase9/media',
       'S3_REGION': 'us-east-1',
       'S3_ENDPOINT_URL': 'http://127.0.0.1:59000',
       'S3_PUBLIC_BASE_URL': 'http://localhost:59000/pixshare-media-test',
       'S3_ADDRESSING_STYLE': 'path',
       'S3_ACCESS_KEY_ID': secrets.token_hex(12),
       'S3_SECRET_ACCESS_KEY': secrets.token_urlsafe(32),
       'S3_INTEGRATION_TEST': '1',
   }
   fd = os.open('.env.s3-test', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
   with os.fdopen(fd, 'w') as output:
       output.writelines(f'{key}={value}\n' for key, value in values.items())
   PY
   docker compose --env-file .env.s3-test -f docker-compose.s3-test.yaml up -d --build --wait
   uv run --env-file .env.s3-test python -m scripts.setup_s3_test
   ```

   Setup refuses nonlocal endpoints, buckets without a `-test` suffix or missing
   explicit test credentials/opt-in. It creates only the dedicated test bucket
   and a policy permitting anonymous GET on `phase9/*/original.*` and
   `phase9/*/variants/*.webp`. No anonymous list, mutation or manifest read is
   granted. Each integration test uses a unique `phase9/tests/<random>` prefix
   and removes only its own objects.
3. Create two new disposable databases on your local PostgreSQL server:
   `pixshare_storage_test` for pytest and `pixshare_s3_browser` for browser data.
   The URL above assumes the development-only `postgres` credentials and port
   5432; adjust it privately to your isolated server. Never substitute an existing
   application database. Migrate only these new databases using the existing
   Alembic history. Pytest fixtures delete rows, so its database must end `_test`.
   For the example development connection:

   ```bash
   export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/pixshare_storage_test
   DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head
   uv run --env-file .env.s3-test alembic upgrade head
   uv run --env-file .env.s3-test python -m scripts.seed_db
   ```

   With the disposable test URL exported, run the entire suite from the root:

   ```bash
   S3_INTEGRATION_TEST=1 S3_INTEGRATION_ENV_FILE=.env.s3-test uv run pytest -q
   uv run ruff check .
   uv run basedpyright
   ```

   Without the explicit opt-in, S3 integration cases are skipped with a reason;
   the filesystem regression suite remains available without an object server.
4. Browser checks use the **separate disposable browser database** and upload
   directory explicitly configured in `.env.s3-test` above. Seed uses LocalStorage,
   intentionally keeping existing/legacy URL behavior even with S3 selected.
   Start the API with that database, upload directory and the ignored S3 env file:

   ```bash
   uv run --env-file .env.s3-test uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
   ```

   The root ignored `.env` still supplies matching development Clerk keys.
   Ensure `web/.env.local` and `web/.env.e2e.local` configure the same Clerk
   instance and two distinct dedicated test accounts as documented in
   [authentication verification](AUTH_VERIFICATION.md). Existing accounts suffice.
   Build/start the frontend, then run:

   ```bash
   cd web
   pnpm lint
   pnpm typecheck
   pnpm build
   pnpm start
   # In another terminal, also in web:
   E2E_BASE_URL=http://localhost:3000 E2E_REQUIRE_AUTH=1 \
     E2E_MEDIA_BASE_URL=http://localhost:59000/pixshare-media-test pnpm test:e2e
   ```

   Choose an installed Playwright Chromium or set
   `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to its actual executable. A public S3
   fixture with multiple variants lets the public variant-selection test exercise
   absolute URLs as well; the authenticated workflow always verifies new S3 media.
   Do not seed, reconcile or run browser mutations against an application database.
5. Stop only this test service with `docker compose --env-file .env.s3-test -f
   docker-compose.s3-test.yaml stop`. Keep its named volume and private env file
   together for persistence; do not use `down -v` on media you intend to retain.

## Cross-browser container procedure

The isolated browser image matches the installed Playwright 1.64.1 exactly:
`mcr.microsoft.com/playwright:v1.64.1-noble`, downloaded digest
`sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea`.
It supplies Firefox 157.0 and WebKit 27.2 with compatible system libraries. The
host's previous missing-library limitation therefore does not require modifying
host libraries. Browsers run as the host's nonroot UID, with default container
security settings; no browser sandbox-disabling flag was added.

With the isolated S3 API and production frontend already running on localhost,
run from the repository root on Linux:

```bash
mkdir -p /tmp/pixshare-cross-browser-results
docker run --rm --user "$(id -u):$(id -g)" --network host --ipc host \
  --env E2E_BASE_URL=http://localhost:3000 \
  --env E2E_REQUIRE_AUTH=1 --env E2E_CROSS_BROWSER=1 \
  --env E2E_MEDIA_BASE_URL=http://localhost:59000/pixshare-media-test \
  --mount type=bind,source="$PWD/web",target=/work/web,readonly \
  --mount type=bind,source="$PWD/demo",target=/work/demo,readonly \
  --mount type=bind,source=/tmp/pixshare-cross-browser-results,target=/results \
  --workdir /work/web mcr.microsoft.com/playwright:v1.64.1-noble \
  node node_modules/@playwright/test/cli.js test \
  --project=firefox-public --project=firefox-auth \
  --project=webkit-public --project=webkit-auth --output=/results/run
```

Only `web` and demo fixtures are mounted read-only, plus writable isolated test
results; backend `.env`, AWS credential directories and S3 secrets are not
mounted. The ignored web environment supplies the existing dedicated Clerk test
configuration to the test runner. Authenticated screenshots, traces and videos
remain disabled to avoid capturing account details; public failure artifacts are
local only. Host networking keeps the established localhost Clerk/API origins.
These are Linux container instructions, not a claim of native Safari testing.

## Failure recovery

| Failure | Behavior |
| --- | --- |
| Invalid file/content/dimensions | Existing API validation rejects it before storage |
| Original PUT / network failure | Generic HTTP 503; no new Post; owned ambiguous writes are cleaned when provable |
| Encoder / variant / manifest PUT failure | Original retained; partial publication removed where storage permits; optional metadata falls back |
| Metadata read outage | Sanitized warning and original delivery |
| Database commit failure | Rollback; clean the new group; preserve the old record/media |
| Refresh failure after committed replacement | Error response may occur, but committed replacement remains and old media is cleaned |
| Post-commit deletion failure | Database result remains successful; sanitized reconciliation warning |
| Batch delete returns HTTP 200 with per-key errors | Inspect errors; bounded retry of transient failures; permanent failures remain visible |
| Crash, cancellation or cleanup outage | Orphans can remain; no automatic live-data sweep |

Paginated listings and 1,000-key delete batches handle complete groups.
The SDK retries transient request failures; per-key transient batch errors also
receive bounded retries. These are per-request timeouts, not a global HTTP request
deadline. Unknown original-write ownership is deliberately retained for audit
rather than risking deletion of another request's object.

`python -m scripts.reconcile_media --report media-reports/audit.json` inventories
unreferenced S3 groups older than 24 hours by default (minimum permitted grace:
one hour). Create `media-reports/` first. Reports are created exclusively with
mode 0600 and are ignored by Git; stdout contains aggregate counts only.
Review the intended database, bucket, prefix and report. To remove candidates,
**pause and drain every media writer first**, then explicitly supply `--apply
--writes-paused` and a new report path. The command refreshes group age and
checks current database references before each removal. The flag asserts an
operator-maintained maintenance window; it does not pause application traffic.
If cleanup fails, some groups may already be removed and the new report may be
incomplete. Preserve the reviewed dry-run report and run another dry-run to
inspect remaining candidates; do not interpret failure as zero deletions.

Cleanup inventories only whole unreferenced groups. Extra objects inside a live
group, historical versions and failed multipart uploads are outside this tool's
scope. This implementation uses small single PUTs, not multipart uploads. Local
filesystem orphan reconciliation remains manual. No cleanup command was applied
to existing user data during this phase; apply behavior was tested only inside
owned integration-test namespaces. A CLI dry-run against the disposable S3
browser database reported zero candidates and zero removals.

## Verification results

| Check | Result |
| --- | --- |
| Complete backend suite, real PostgreSQL + MinIO | **PASS — 114 tests**, 17.27s; zero skipped |
| Existing backend regression coverage | Included: 84 tests |
| New configuration / safe initialization cases | Included: 16 cases |
| Real S3 integration / failure-recovery cases | Included: 14 cases |
| Ruff | **PASS** — no findings |
| basedpyright | **PASS** — 0 errors, 0 warnings |
| Frontend `pnpm lint` | **PASS** |
| Frontend `pnpm typecheck` | **PASS** |
| Frontend `pnpm build` | **PASS** — optimized Next.js production build |
| Chromium, local filesystem provider | **PASS — 24 tests**, 2.9 minutes; zero skipped |
| Chromium, S3 provider with mixed legacy/S3 data | **PASS — 24 tests**, 2.9 minutes; zero skipped |
| Chromium after shared browser-helper repairs | **PASS — 9 affected checks**, 2.1 minutes; setup, all 5 auth journeys and responsive/theme checks at all 3 layouts |
| Firefox public + authenticated S3 workflows | **PASS — all 11 scenarios verified** across initial run and affected rerun |
| WebKit public + authenticated S3 workflows | **PASS — all 11 scenarios verified** across initial run and affected rerun |
| Combined Firefox/WebKit execution history | Initial run **17 passed / 6 failed**; repaired shared helpers and assertions; affected rerun **13 passed**, 4.6 minutes, zero skipped (includes setup) |
| Actual object-server outage / recovery | **PASS** — stopped MinIO; SDK upload returned a sanitized failure in 1.03s under the configured two-attempt policy; restarted healthy; S3 original/all variants and three local fixtures intact; no temporary browser posts left |
| Container restart persistence | **PASS** — original SHA-256 unchanged; private manifest and every variant decoded/read after restart; probe removed |
| Anonymous S3 permissions | **PASS** — public original/variant GET; denied list/manifest GET, PUT and DELETE |
| Orphan reconciler CLI dry-run | **PASS** — zero candidates/removals on disposable S3 browser database; private report created |
| Changed-file privacy review | **PASS** — configured secrets/tokens/account addresses absent from changed files |
| `git diff --check` | **PASS** |

The first Firefox/WebKit run exposed test-harness failures: Firefox's 44px
bounding box rounded to `43.99993896484375`, a theme assertion read the DOM before
its update, Clerk sign-in/sign-out redirects raced the next `page.goto`, and a
broad status locator matched both deletion success and gallery loading. Repairs
allow only 0.001px layout precision, await observable UI/session transitions and
select the actual success status. No authentication or ownership assertion was
removed. One intermediate Firefox-only check passed the size assertion but
failed the immediate theme snapshot; the web-first DOM assertion then passed in
both engines. All 10 authenticated scenarios and both responsive/theme scenarios
were rerun after the shared helper changes. The other 10 public scenarios had
already passed and were unchanged.

WebKit emitted intermittent Clerk development-handshake warnings about HTML
responses where the testing SDK expected JSON. Its built-in retries continued;
all final authenticated journeys passed with actual sessions and backend
ownership verification. This remains a development SDK/environment warning,
not evidence of native Safari or production Clerk verification. The frontend
server also logged Clerk session-refresh/infinite-redirect warnings during these
runs. Private comparisons confirmed that the configured server secret keys match
and the root/frontend publishable keys match; no credentials were changed.
The backend's separate optional publishable-key setting is unused. The warning's
underlying cause is **unresolved** despite passing journeys; production Clerk
session behavior and native Safari remain unverified.

A first container invocation also needed its output changed from the
bind-mount root `/results` to a writable child `/results/run`, because Playwright
cleans the output directory before running.

Backend execution used `S3_INTEGRATION_TEST=1`, a private
`S3_INTEGRATION_ENV_FILE`, the dedicated `_test` database and a separate uploads
path. Successful storage operations use actual MinIO HTTP calls, not Moto or
mock S3 responses. Fault tests wrap individual operations to inject ambiguous
writes, publication failures, per-key deletion errors, metadata outages and
database failures while retaining real object I/O and cleanup assertions.
Authentication is mocked only by the existing backend unit-test fixture;
browser authentication uses real Clerk development sessions verified by the API.

This workstation needs its Nix GCC library path for Python extension modules and
a Nix dynamic loader for the locked Ruff executable. Ruff and basedpyright were
executed directly from the installed locked environment (the equivalent of the
repository's `uv run ruff check .` and `uv run basedpyright` commands). No checks
were disabled to accommodate those tool-launch requirements.

## Deployment requirements and remaining risks

- Development Clerk handshake/session-refresh warnings remain unresolved despite
  successful real-account workflows and matching configured keys. Validate the
  intended production Clerk configuration and browser session behavior before
  rollout; changing credentials without evidence is not a remedy.
- AWS IAM, CloudFront/CDN configuration, encryption, region-specific behavior,
  bucket versioning/object-lock policies, backups and restores have **not** been
  verified against AWS. No cloud resources were provisioned. Test these in the
  intended deployment environment before rollout.
- Local MinIO compatibility does not establish equivalence of every S3 vendor.
  The archived test fixture must not become an exposed production service.
- S3 and PostgreSQL cannot share a transaction. There is no durable cleanup outbox
  or mutation idempotency key; failures can leave orphans, and manually retrying a
  committed create after an error can duplicate a post. Monitor sanitized warnings.
- Normal deletion in a versioned bucket creates delete markers; historical bytes
  need lifecycle/retention management. Object lock can prevent physical cleanup.
- Public cached media can outlive deletion. Originals preserve source metadata,
  including possible location data, exactly as before. Define privacy, retention,
  moderation and takedown policies before public operation.
- Keep ingress upload/body/concurrency limits, HTTPS, explicit CORS/Clerk origins,
  readiness monitoring and backups. Variant generation bounds per-process raster
  work, but worker count and simultaneous request bodies affect total memory.
- No API/UI feature redesign, production rollout, account changes or destructive
  migration is included. The optional legacy backfill was not run.

## Sources checked against installed behavior

- [Boto3 PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)
  and [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
  for content types, SigV4 and conditional original creation.
- [Boto3 retries](https://docs.aws.amazon.com/boto3/latest/guide/retries.html)
  for standard retries and total-attempt semantics.
- [S3 DeleteObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html)
  for per-key errors, batch limits and versioned-delete behavior.
- [S3 consistency](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
  for manifest-last publication assumptions on AWS S3.
- [MinIO upstream](https://github.com/minio/minio) for archive/source status and
  the pinned local compatibility fixture.
- [Playwright Docker documentation](https://playwright.dev/docs/docker) for a
  matching browser/tool version and nonroot container execution.
