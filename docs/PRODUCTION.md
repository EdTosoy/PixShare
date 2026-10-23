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
  Add readiness checks and authenticated operational access in deployment config.
- Images are public and preserve their original bytes, including metadata.
  Define metadata stripping, moderation, retention, takedown and account deletion
  policies for the intended product; these are not implemented by this MVP.

## Storage and S3-compatible investigation

The existing `Storage` interface supports `upload(BinaryIO, filename,
content_type) -> URL` and `delete(URL)`. Local disk is implemented and remains
the free default. A future S3 adapter can use the same route lifecycle without
changing Post records or endpoint contracts.

Proposed adapter design (not installed or exercised here):

1. Add an optional `boto3` dependency and select the adapter in `get_storage()`
   with explicit bucket, endpoint, region and public media-base configuration.
   Keep credentials in the standard server-side AWS credential chain.
2. Upload a random immutable object key using `upload_fileobj`, setting the
   validated ContentType. Run synchronous SDK work in a worker thread.
   [Boto3 upload contract](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_fileobj.html).
3. Return a stable HTTPS media/CDN URL. Store durable identifiers, never an
   expiring signed URL, in `Post.url`. If images become private, add signed-read
   URL generation at response time and update the public API contract explicitly.
4. Delete only keys whose URL belongs to the configured media namespace.
   Retry transient failures and retain the route's commit-first ordering.
   Account for bucket versioning: deletion can create a delete marker instead
   of purging older bytes. [Boto3 deletion behavior](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/delete_object.html).
5. Validate the adapter against a local Moto server using dummy credentials,
   a custom endpoint, and real SDK HTTP calls. No cloud account is required.
   Moto supports both path/host bucket addressing and custom S3 endpoints.
   [Moto S3 reference](https://docs.getmoto.org/en/latest/docs/services/s3.html).
   This is adapter integration evidence, not proof of a particular vendor's IAM,
   CDN, multipart or consistency behavior; test those before a real rollout.

LocalStorage's persistent volume is suitable for a single API instance. Multiple
replicas require a shared filesystem or the object-store adapter. The frontend
currently downloads originals directly; cache headers and thumbnail/CDN sizing
should be designed together when scaling image traffic.

## Cross-resource failure limits

Storage and PostgreSQL cannot share a transaction. Commit failures are tested to
clean new files and preserve existing files. Cleanup failures after commit leave
an orphan rather than a database row referencing missing media. A process crash
between storage write and commit can also leave an orphan.

Reconciliation is manual: compare storage keys with committed Post URLs, use a
conservative grace period for in-flight uploads, review candidates, and remove
only confirmed unreferenced objects. Do not automate deletion against live media
without a reviewed retention policy. A durable cleanup outbox is a future option
if real failure volume warrants it; it is unnecessary for local MVP operation.

A commit followed by a response-refresh failure can produce 500 even though the
write succeeded. Automatic create retries can duplicate posts; the frontend does
not automatically retry mutations. An idempotency-key contract would be needed
for transparent create retry. Offset pagination is stable for a fixed dataset;
concurrent additions/removals can shift page boundaries.
