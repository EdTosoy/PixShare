# Production-readiness review

No infrastructure was provisioned or deployed. These are deployment decisions
and remaining operational work, not claims of a production rollout.

## Configuration and security

- PostgreSQL remains the only database. Preserve both existing Alembic revisions.
  Back up and restore-test database and media together. Migrate once before
  rollout; Compose's startup migration is intended for a single local API.
- Set `CORS_ORIGINS` and `CLERK_AUTHORIZED_PARTIES` to explicit frontend origins.
  CORS is configurable; ownership is always enforced separately in the API.
  JWT signatures, time claims and authorized parties use Clerk's installed SDK.
  Keep the frontend/API on the same Clerk instance and set correct production
  Clerk domain/redirect configuration before rollout.
- Keep secret keys server-side. Do not build secrets into the frontend. The
  public API origin and publishable key require a rebuild when changed.
- SQL echo is disabled and SQLAlchemy hides parameters. Database errors return
  a generic response. Media-cleanup logs omit URLs and exception text.
  Add structured request IDs and operational alerts before sustained public use;
  avoid logging Bearer headers, tokens, captions, or SQL parameter values.
- Require HTTPS at ingress and cap multipart requests (allow overhead beyond
  the 10 MiB image limit). Pillow bounds decoded image hazards, but multipart
  parsing occurs before route validation. Apply ingress rate/concurrency limits.
- Containers run as nonroot. Local Compose ports bind to loopback and database
  credentials are for development. `/health` is liveness, not DB readiness.
  `/ready` now checks database/table access with a deadline. Keep operational
  access restricted; readiness does not verify Clerk, S3 or the complete schema.
- Images are public and preserve their original bytes, including metadata.
  Define metadata stripping, moderation, retention, takedown and account deletion
  policies for the intended product; these are not implemented by this MVP.

## Storage deployment

Local disk remains the default. The implemented S3-compatible adapter uses boto3
with SigV4, conditional original writes, bounded retries/timeouts and immutable
object groups. It shares the existing image limits, variants and commit-first
lifecycle. Select it with `STORAGE_PROVIDER=s3`; configure `S3_BUCKET`,
`S3_PREFIX`, `S3_REGION` and `S3_PUBLIC_BASE_URL` server-side. AWS normally leaves
`S3_ENDPOINT_URL` unset and uses an IAM role; compatible services set their HTTPS
endpoint and addressing style. Explicit credentials are optional server secrets.

Configure a public image/CDN origin before enabling new writes. Prefer a private
S3 bucket behind a public CloudFront distribution with origin access control;
if serving a bucket directly, grant anonymous GET only on original/variant paths.
Never permit anonymous listing, writes, deletes or manifest reads. Browser
uploads still go through the Clerk-authenticated API and ownership checks.
Do not disable bucket security globally to get a test passing.

Grant the API role only prefix-scoped ListBucket plus GetObject, PutObject and
DeleteObject for its media namespace. No ACL or bucket-management permission is
needed at runtime. Establish encryption, backups, lifecycle and noncurrent-version
retention policies independently. Delete markers are not a purge of historical
versions; object-lock retention may block cleanup. Test the actual deployment's
IAM, TLS, CDN, caching and restore behavior before rollout.

The local volume is still required for existing `/uploads/` records. Retain the S3
configuration if switching new writes back to local. Neither switch migrates
existing data. Public-base changes are resolved at read time; bucket/prefix
changes require a separate migration. Multiple replicas can share object storage,
but legacy local files still require shared storage or a planned migration.

[Phase 9](PHASE_9_REPORT.md) documents the isolated real MinIO compatibility
environment, restart test, commands and results. It provisions no AWS resources.
The pinned community MinIO server is archived upstream and is used only as a
local test fixture, not a production storage recommendation.

## Cross-resource failure limits

Storage and PostgreSQL cannot share a transaction. Commit failures are tested to
clean new files and preserve existing files. Cleanup failures after commit leave
an orphan rather than a database row referencing missing media. A process crash
between storage write and commit can also leave an orphan.

S3 reconciliation is operator-controlled via `scripts.reconcile_media`, dry-run
by default. Review its private report, pause and drain all media writers, retain a
conservative grace period, then explicitly opt into removal. It rechecks object
age and database references before deleting each candidate group. It does not
automatically retry post-commit cleanup or inspect historical object versions.
Local-filesystem orphan reconciliation remains manual. Do not automate deletion
against live media without a reviewed retention policy. A durable cleanup outbox is a future option
if real failure volume warrants it; it is unnecessary for local MVP operation.

A commit followed by a response-refresh failure can produce 500 even though the
write succeeded. Automatic create retries can duplicate posts; the frontend does
not automatically retry mutations. An idempotency-key contract would be needed
for transparent create retry. Offset pagination is stable for a fixed dataset;
concurrent additions/removals can shift page boundaries.

## Phase 10 release candidate

Production configuration now fails closed for development Clerk secrets, missing
HTTPS origin allowlists and missing API hostnames. The API requires explicit
Bearer credentials, bounds raw bodies before multipart parsing and supplies a
bounded per-process rate limiter. Shared ingress limits are still required.
Database pool/acquire/command timeouts and readiness are configurable.

Use the [Phase 10 report](PHASE_10_REPORT.md) and
[deployment runbook](DEPLOYMENT_RUNBOOK.md) for current audit results, patched
dependency versions, isolated recovery evidence, production examples and hard
release gates. Existing Phase 8 images are incompatible rollback targets after
S3 writes; no public deployment is approved by these local checks.
