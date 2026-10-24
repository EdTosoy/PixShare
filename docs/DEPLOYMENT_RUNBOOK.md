# PixShare deployment and recovery runbook

Status: release-candidate procedure, 2026-10-24. **No production deployment has
been performed.** See [Phase 10 assessment](PHASE_10_REPORT.md) for executed
checks, limitations and go/no-go gates. Commands below are operator instructions,
not authorization to provision resources or modify live infrastructure.

## 1. Establish the release boundary

Use a reviewed, committed revision and immutable API/web image digests. The
working tree currently includes uncommitted Phase 9 and Phase 10 work; do not
build a public release from an unidentified working tree. Commit/push/publishing
require separate authorization. Record revision, lockfile hashes, image digests,
scan results, migration head, frontend public configuration and rollback image.
Never include private environment contents in this record.

Infrastructure: HTTPS ingress → Next.js and FastAPI; FastAPI → private
PostgreSQL and S3. Browsers fetch originals/variants from a public CDN with a
private S3 origin. PostgreSQL and S3 credentials are never browser configuration.
Retain the existing uploads volume for legacy `/uploads/` references.

The default `docker-compose.yaml` is a development stack. The standalone
`docker-compose.production.yaml` is a reviewed starting point for external
PostgreSQL/S3 and an **existing** HTTPS ingress. It does not provision TLS, DNS,
AWS, PostgreSQL, a CDN or monitoring. Its legacy uploads volume must already
exist. Do not run `up` until the gates in the report are satisfied.

## 2. Prepare configuration privately

Copy [`.env.production.example`](../.env.production.example) to a protected file
outside Git, replace every placeholder, restrict permissions to 0600, and inject
values through the deployment's secret manager. The production Compose example
accepts `PIXSHARE_API_ENV_FILE` for the API's private file. The web service receives
only its Clerk runtime settings, not database/S3 credentials. Do not print
`docker compose config`, `env`, settings objects or secret files. Use
`docker compose ... config --quiet` for syntax validation.

Backend requirements:

- `ENVIRONMENT=production`; exact `ALLOWED_HOSTS` API hostname(s).
- Private PostgreSQL `DATABASE_URL`, preferably TLS with certificate verification
  (`?ssl=verify-full` with the installed asyncpg driver). Use a non-superuser
  application role. Restrict database ingress to application/operations networks.
  Use a separate migration/restore role where supported. Never use development
  `postgres/postgres` credentials for production.
- Live `CLERK_SECRET_KEY` or a trusted production `CLERK_JWT_KEY` PEM. If a secret
  is also supplied it must be a live key. Configure explicit HTTPS
  `CLERK_AUTHORIZED_PARTIES` and `CORS_ORIGINS`, without wildcards, paths or trailing
  slashes. Every CORS origin must be authorized. These guards fail closed.
- `STORAGE_PROVIDER=s3`, a configured `S3_BUCKET`, immutable `S3_PREFIX`, region and
  HTTPS `S3_PUBLIC_BASE_URL`. Leave `S3_ENDPOINT_URL` empty on AWS; set an HTTPS
  endpoint/addressing style for another service. Prefer the server IAM role;
  explicit S3 credentials/session tokens remain server secrets.
- Preserve `UPLOADS_DIR=/app/uploads` and map `PIXSHARE_UPLOADS_VOLUME` to the
  **existing** volume. Do not silently substitute an empty volume.
- Review the default pool budget (5 + 5 overflow connections per API process),
  5s acquire/connect timeout, 15s DB command timeout and 3s readiness deadline.
  Sum pool budgets across replicas and reserve database capacity for operations.

Frontend public **build-time** values:

```bash
# Run only after approval with reviewed public production values in the shell.
# Secret keys are never build arguments.
docker build -f web/Dockerfile \
  --build-arg PIXSHARE_ENVIRONMENT=production \
  --build-arg NEXT_PUBLIC_API_URL \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \
  -t "$PIXSHARE_WEB_IMAGE" web
```

Use a live publishable key and HTTPS API origin. Public values are frozen in the
image: rebuild rather than changing only runtime environment. Runtime requires
`PIXSHARE_ENVIRONMENT=production`, the matching `CLERK_SECRET_KEY` and explicit
`CLERK_AUTHORIZED_PARTIES`. Never use `NEXT_PUBLIC_` for a secret. Validate the
actual live-key image in staging; local checks use development Clerk accounts.

## 3. Configure production Clerk without changing development users

1. Create/select the intended production instance in Clerk and configure its
   production application/FAPI domains, DNS and certificates. This runbook does
   not create an instance or alter existing accounts.
2. Copy matching live publishable/secret keys into the appropriate secret-manager
   entries. Configure sign-in methods, OAuth provider production credentials,
   allowed redirects, `/sign-in`, `/sign-up` and `/me` fallbacks.
3. Configure exact HTTPS authorized parties on both the web middleware and API.
   Keep a single canonical browser origin. Review proxy Host/X-Forwarded headers
   and Clerk domain configuration; do not interchange localhost/127.0.0.1.
4. Test sign-up, sign-in, sign-out, session renewal after token expiration,
   two-account ownership, reloads and multiple tabs on all supported browsers.
   Check sanitized application/Clerk diagnostics for persistent handshakes.
5. Development and production Clerk instances have different identities. Existing
   development users/accounts/data are preserved; they are **not automatically
   migrated or reassigned**. If existing records must move to production, approve
   and test an identity/data migration plan separately. Never rewrite ownership
   to make a production smoke test pass.

Do not apply the Playwright testing-token/handshake interception to application
traffic. It exists only in the E2E harness. See the report for the exact
reproduced development warnings and their diagnosis.

## 4. Configure S3/CDN least privilege

Keep S3 Block Public Access enabled for the recommended private bucket + public
CDN design. Use CloudFront origin access control or an equivalent maintained
vendor facility. Restrict origin-read permission to originals and WebP variants;
keep manifests private. Do not allow anonymous list, upload, overwrite or delete.
No presigned browser-write flow exists; API mutations require a Bearer session
and backend ownership checks.

Illustrative **API-role** policy (replace bucket/prefix; review in staging):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "s3:ListBucket",
     "Resource": "arn:aws:s3:::REPLACE_BUCKET",
     "Condition": {"StringLike": {"s3:prefix": ["pixshare/media/*"]}}},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": "arn:aws:s3:::REPLACE_BUCKET/pixshare/media/*"}
  ]
}
```

No runtime CreateBucket, PutBucketPolicy, ACL or DeleteBucket permission is
needed. A CDN origin role should GET only
`pixshare/media/*/original.*` and `pixshare/media/*/variants/*.webp`, constrained
to the specific distribution. Review the actual bucket policy with the provider;
this policy fragment is not a claim of verified AWS IAM. Configure encryption,
versioning, retention, lifecycle and separate backup access. Noncurrent versions
and object lock can change physical deletion behavior.

Do not forward viewer cookies or Authorization to the public image origin or
include them in public-media cache keys. Use a CDN response-headers policy for `nosniff`, HTTPS/HSTS and the product's
public-media cache policy. API variants and S3 originals use immutable unique
keys and long cache lifetimes; caches can outlive deletion. Define a takedown/
invalidation procedure. Original bytes, including possible EXIF/GPS, are retained.
Obtain product/privacy acceptance before public exposure.

The public base can change without rewriting records. Bucket/prefix changes
cannot: database references contain those durable identifiers. Plan migrations
separately. Community MinIO in `dev/minio` is an archived, loopback-only
compatibility fixture; do not deploy it as the production storage service.

## 5. Ingress, resources and logging

Terminate HTTPS at a maintained ingress. Publish only the application/API routes;
keep database, container ports and operations endpoints restricted. The example
Compose ports bind to loopback. For a containerized ingress use a private network
and appropriate routing rather than exposing the API globally.

For an Nginx-style ingress, overwrite forwarded host/protocol headers rather
than accepting client-supplied values; restrict the listener to the canonical
`server_name`. An equivalent provider configuration is acceptable:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
client_max_body_size 11m;
client_body_timeout 30s;
proxy_read_timeout 60s;
```

Canonical host/protocol alignment is especially important for Clerk handshakes.
Local verification uses the start script's `localhost` bind and the same browser
hostname; changing only one side to a literal IP caused timeouts in this audit.
Production ingress/header behavior still requires its own staging smoke test.

Configure at least:

- Raw request body cap **11 MiB**, allowing the 10 MiB file plus caption/multipart
  overhead. Reject oversized/chunked requests before application spooling.
- Shared edge rate limits across replicas: start with 300 reads/minute and 60
  writes/minute per client, then tune from legitimate traffic. Treat Clerk login
  endpoints separately according to provider guidance. Limit unauthenticated
  abuse, concurrent uploads and connection counts at ingress.
- Body/read timeouts (30s body; a reviewed application-response deadline such as
  60s), bounded upstream concurrency and keep-alive. Tune against real media,
  network latency and vendor throttling before rollout.
- `FORWARDED_ALLOW_IPS` restricted to the actual ingress IP/CIDR; never `*` on a
  reachable API. The application rate limiter trusts the ASGI peer after Uvicorn's
  configured proxy handling and ignores raw spoofed X-Forwarded-For headers.
- HTTPS redirect, HSTS only after TLS is confirmed, request IDs and access logs
  containing sanitized paths/status/timing. Redact query strings, Authorization,
  cookies, JWTs, SQL values, environment contents and request/response bodies.

The API also enforces its raw-body cap/deadline and bounded per-process fixed
minute-window counters. Its 10,000-entry LRU table is a fallback, **not a shared
abuse service**: counters reset on restart, can be evicted under IP churn and are
not shared across replicas. NAT users may share quotas. The production ingress
must enforce global limits independently.

The Compose example starts with one API CPU, 1 GiB memory, one worker, eight
concurrent requests, 128 queued connections/processes and bounded tmpfs/log
storage. These are initial bounds, not measured capacity guarantees. Decode/
resize work is serialized per API process; increasing workers multiplies memory
and DB pools. Monitor CPU/RSS, spool space, latency, 413/408/429/503 rates, DB pool
pressure and sanitized media-cleanup warnings. Alert rather than automatically
retrying a mutation whose commit status is unknown.

Baseline web headers include nosniff, anti-framing, referrer and permissions
policies, and CSP `frame-ancestors`, `base-uri` and `object-src`. A full script/
connect CSP requires deployment-specific Clerk/CDN origins and nonce review;
roll it out in report-only mode first, then verify before enforcement. Do not
block Clerk/captcha/Next scripts through an untested policy.

## 6. Preflight, migrations and traffic cutover

1. Complete every hard gate in [Phase 10](PHASE_10_REPORT.md). Re-run dependency
   and container-image scans on the exact immutable artifacts. Scan all images,
   including OS/native libraries; the local pip/npm scans alone do not cover them.
2. Take and restore-test a coordinated database/media backup. Record a safe
   rollback image that understands S3 references and includes security patches.
3. Quiesce/drain writers for the backup/migration window. Run migrations **once**
   with the reviewed release image and migration role, using the approved private
   runtime configuration. Do not let every API replica auto-migrate.

   ```bash
   # Future operator action only; never run against an unreviewed database.
   docker compose --env-file "$DEPLOY_ENV" -f docker-compose.production.yaml \
     run --rm --no-deps api /app/.venv/bin/alembic current
   docker compose --env-file "$DEPLOY_ENV" -f docker-compose.production.yaml \
     run --rm --no-deps api /app/.venv/bin/alembic upgrade head
   ```

   Existing head is `cdae1ace538f`; Phase 9/10 add no revisions or destructive
   migrations. Check the release's actual head and schema compatibility before
   executing. Never automatically run `alembic downgrade` as rollback.
4. Start candidate containers behind ingress without routing public traffic.
   `/health` verifies process liveness. `/ready` requires a DB connection and
   posts/users tables within a bounded deadline; it does **not** certify every
   migration, Clerk, S3, CDN or DNS. Check the Alembic head separately.
5. Verify web static health, public galleries, legacy media, new CDN variants,
   authenticated uploads/replacement/deletion, ownership and error feedback.
   Check image content types and anonymous-denial policies. Run axe/keyboard,
   theme/mobile and all three engine journeys on the real staging origins.
6. Perform canary cutover. Watch readiness, latency/error rates, auth warnings,
   memory, DB/storage and ingress limits. Resume writers and expand only after
   the agreed observation window. Keep the previous safe artifact available.

## 7. Coordinated backup and restore

Define an owner, frequency, retention, encryption, offsite/immutable copy, RPO and
RTO. A reasonable initial **target**, not a verified production SLA, is RPO ≤24h
and RTO ≤2h; choose stricter targets if user impact requires them. Use managed
PostgreSQL PITR if available and verify its retention/restore process.

For a consistent full backup, pause/drain **all** media writers, then capture:

1. `pg_dump --format=custom --no-owner --no-acl` with a compatible PostgreSQL
   client, a protected `PGPASSFILE`/service configuration and restricted backup
   role. Keep credentials out of command-line URLs. Restore into a fresh isolated
   DB with `pg_restore --exit-on-error --no-owner --no-acl` and the approved role.
2. The full legacy uploads volume, including `_variants` manifests/bundles.
   Restore ownership/permissions for container UID 10001. Inspect archive paths;
   use safe extraction and never extract an untrusted archive into a live volume.
3. Every S3 object in the media namespace, including **private manifests**, plus
   metadata/content types, bucket policy/configuration inventory and version IDs
   where versioning is used. Store checksum inventories privately. Retaining only
   public thumbnails is not a backup.
4. Migration/release identifiers and references to the secret-manager versions
   needed for recovery. Keep secret values separately protected, not in reports.

Restore to new isolated DB/filesystem/object endpoints first. Preserve durable
bucket/key identities or explicitly plan a reference migration in the restored
copy. Switch endpoint/public base at response time where possible. Validate row
counts/IDs/owners, hashes, manifests, dimensions and HTTP reads, then authenticated
journeys and denial policies before any production recovery cutover.

S3 versioning is useful retention, not a coordinated database backup. A database
point-in-time restore requires the corresponding object inventory/version state.
Restoring just the database can reference missing images or undo legitimate
ownership/deletions. Never delete retained versions to make a restore appear tidy.

The local drill used separate PostgreSQL and MinIO containers and fresh paths;
no application data was overwritten. It does not establish managed PITR, regional
failover, production TLS/IAM or the production RPO/RTO.

## 8. Failure and rollback actions

| Symptom | Action |
| --- | --- |
| `/ready` 503, `/health` 200 | Hold/drain traffic; inspect DB reachability, pool pressure, TLS and schema using private operational diagnostics; restore DB service; require readiness recovery |
| S3 outage | Keep originals/references; hold mutations or communicate failures; restore storage access; check unchanged objects and sanitized cleanup alerts |
| Bad application release | Stop traffic/writers as required; switch to the tested **S3-capable, security-patched** rollback image; retain DB/media and compatible config |
| Suspected credential exposure | Restrict ingress, rotate/revoke through approved procedures, invalidate affected sessions if indicated, investigate private evidence; never print the key |
| Database/media corruption | Stop writers; restore coordinated snapshot into isolated targets; validate; approve recovery cutover separately |
| Orphan-cleanup warning | Follow the dry-run/review/maintenance procedure below; do not sweep active media |

**Do not roll back to main `632b15c` after S3 writes.** That Phase 8 image does not
understand `s3://` references. A rollback target must support the new references
and patched security dependencies. If none is available, use maintenance mode
and preserve data rather than installing an incompatible image or restoring an
old DB alone. The release must establish a safe rollback artifact before launch.

For orphan cleanup, configure the intended DB/bucket/prefix privately, create
`media-reports/`, and run `python -m scripts.reconcile_media --report ...` for a
private dry-run inventory. Default grace is 24h, minimum 1h. Review it, pause and
drain every writer, then use a new report path with `--apply --writes-paused`.
The flag asserts a maintenance window; it does not stop traffic. Keep the
reviewed dry-run report: a failed apply can remove some groups before failing and
leave an incomplete new report. Re-inventory remaining candidates. It scans only
whole unreferenced groups, not historical versions or extra objects in live
groups. Never run the optional legacy backfill without separate authorization.

## 9. Verification and evidence handling

Reproduce the [Phase 9 isolated service](PHASE_9_REPORT.md), select only fresh
`*_test` and E2E databases, and run the repository's backend/frontend checks.
Use `S3_INTEGRATION_TEST=1` and an ignored dedicated local env file for the real
S3 tests; use `E2E_REQUIRE_AUTH=1` and two existing dedicated Clerk development
accounts. Firefox/WebKit use the matching Playwright container procedure in
Phase 9. Do not run these mutating tests against production.

Keep test artifacts local/private, never publish authenticated traces, cookies,
error contexts, backup dumps, private inventories or environment files. Automated
accessibility scans complement keyboard checks; they do not prove complete WCAG
conformance. Record exact failures/skips and compare only the same tested revision.
