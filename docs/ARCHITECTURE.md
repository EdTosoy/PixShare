# Architecture

PixShare is a modular monolith: one FastAPI API, one Next.js application,
PostgreSQL, and a replaceable storage interface. No queues, microservices,
additional databases, or paid infrastructure are required.

## Request paths

```text
Browser → Next.js App Router → typed browser API client → FastAPI
  Clerk session → Bearer token → Clerk SDK verification → local User
  TanStack Query cache                             ↓
  responsive UI states                 SQLAlchemy async → PostgreSQL
                                                   ↓
                                           Storage interface
                                                   ↓
                                        MediaStorage router
                                        ├ LocalStorage → /uploads
                                        └ S3Storage → S3-compatible bucket
```

Public reads (`GET /posts`, `GET /posts/{id}`) never require Clerk.
Authenticated operations resolve a verified Clerk identity to a local User.
Concurrent first requests tolerate the unique `clerk_id` insert race.
`GET /users/me/posts` filters by that user's database ID; the caller cannot
supply an arbitrary owner. PATCH/DELETE enforce ownership inside the API and
lock the post row, so concurrent replacement/delete requests serialize.

Post arrays keep their existing fields and add nullable `image` metadata. Lists use `(created_at, id)` ordering
and offset pagination. Existing migrations are unchanged; this implementation
needs no schema/data migration.

## Media lifecycle

1. FastAPI parses multipart input; Pillow validates bounded bytes and dimensions
   off the event loop (10 MiB, 16 MP, 20,000px per side).
2. Storage writes a unique original and attempts an atomic WebP variant bundle.
   A complete manifest publishes dimensions and available variants together.
   Optional encoding failure removes partial derivatives and retains the original.
   Local records retain their original URLs. New S3 records store a durable
   `s3://bucket/prefix/group/original.ext` reference; serialization resolves it to
   the configured public image/CDN base. Credentials and private manifests never
   appear in the public response.
3. The database references the new URL and commits.
4. On commit failure: roll back, then clean the new original and every variant.
5. On replacement success: clean the old original/bundle, then refresh the response.
6. On deletion: commit removal of the row before cleaning the original/bundle.

A refresh failure after commit must never cause deletion of the committed image.
Storage-cleanup failures are logged without paths/credentials and do not turn a
successful database mutation into a failed response. PostgreSQL cannot transact
with the filesystem. Crashes and failures may leave orphans; see PRODUCTION.md.

LocalStorage generates canonical image extensions, copies bytes outside the
event loop, removes partial writes on failure, and deletes only its `/uploads/`
namespace. WebP bundles live at `_variants/{original-filename}/`, use bounded
320/640/1280/1920px maximum edges, preserve aspect ratio/transparency and normalize
orientation. Original bytes and metadata are never rewritten. Pillow validation
and generation share one process-local worker lock to limit simultaneous raster
allocations. No queue or cloud processor is required.
`Storage.describe()` returns optional metadata; reads never trigger generation.
Malformed/missing bundles and legacy records fall back to the original. The
explicit row-locked `scripts.backfill_variants` command optimizes compatible old
uploads without changing database rows. See [image/API details](IMAGE_DELIVERY.md).
`UPLOADS_DIR` is shared by the storage dependency, static mount,
and seed script. `MediaStorage` routes existing local references to LocalStorage
even when new writes use S3. Retain the local volume and S3 configuration when
switching providers; no existing rows or images are migrated automatically.

`S3Storage` uses boto3 in worker threads with bounded standard retries, timeouts
and SigV4. Random immutable groups contain the unchanged original, WebP variants
and a private manifest uploaded last. Conditional PUT protects originals from
collisions. Optional derivative failures remove the publication marker before
partial variants, preserving the original. API reads fetch only the small private
manifest, while browsers GET public images directly. Missing metadata falls back
to originals; externally missing derivatives use the browser fallback.

Group deletion handles paginated listings and per-key batch errors. An explicit
`reconcile_media` operator command inventories unreferenced old groups; applying
requires paused writes and fresh reference checks. There is no startup deletion
job. See [Phase 9](PHASE_9_REPORT.md) for configuration and limitations.

## Frontend boundaries

The shared editorial design is recorded in [design.md](../design.md). The landing
page, Explore and personal gallery use the same dimension-aware `PostCard` and
flat, source-ordered gallery layout. Native flex wrapping sizes images by their
metadata ratio; a bounded 4:3 frame covers legacy metadata absence, with contain
fit preserving the full photograph. Mobile stacks in source order. The upload
and edit forms use a two-column picker/caption composition that stacks on mobile.
These are presentation changes; query keys, API parameters and mutations remain
in their existing components. See [final release evidence](FINAL_RELEASE.md).

- `web/app`: route composition; async server params per installed Next 16 docs.
- `web/components`: navigation, gallery, auth states and reusable post controls.
- `web/lib`: typed API access, post contracts and error normalization.
- `web/app/providers.tsx`: real Clerk context and TanStack Query ownership.
- `web/proxy.ts`: Clerk request integration when configured; public otherwise.

The query cache is recreated when Clerk identity changes. Public queries never
request a token; private keys include the user identity. Mutations invalidate
post queries. AuthGate supplies the UI sign-in state; backend checks are the
security boundary. Owner editing waits for ownership resolution rather than
briefly denying access while that query loads.

Images remain browser-direct and laid out at explicit aspect ratios or bounded
detail heights. A shared `PostImage` component provides actual-width WebP srcsets
and responsive `sizes` inside `picture`; Next Image retains the original fallback.
Missing derivatives fall back to the original in the browser as well. Gallery
images are lazy, while details and the existing-image editor preview are eager.
Immutable versioned derivative URLs receive long-lived cache headers. Local
original URLs retain their existing behavior; S3 originals have immutable keys
and long-lived cache headers too. No private-IP optimizer exception or
server-side remote image proxy is enabled. Atelier uses Sentient through the
official Fontshare stylesheet and locally hosted Hanken Grotesk, with Georgia
and Arial fallbacks. Builds do not fetch fonts. Browser display typography
depends on Fontshare availability; see the supplied font notices and licenses.

Caption-based image descriptions and card link names are normalized and bounded
to 160 characters, with neutral fallbacks instead of filenames. Redundant card
image alt text is empty because the enclosing link supplies the description.
Full captions and original filenames remain available on the detail page.
Automated axe scans complement actual keyboard/focus/error-state tests; they
do not establish complete accessibility conformance.

## Release guards and operations

A raw ASGI request guard enforces an 11 MiB total-body budget and 30s receipt
deadline before multipart spooling. Existing file and decoded-image budgets
remain separate. Bounded per-peer minute windows return 429; they are local to
each process and complement, rather than replace, shared ingress abuse limits.
Only explicitly trusted proxy handling may establish the ASGI client address.

Production settings require live/trusted Clerk verification configuration, exact
HTTPS CORS/authorized origins and explicit trusted API hosts. API authentication
accepts Bearer sessions, never ambient cookies. Web proxy authorization uses the
configured origin list and baseline response headers constrain framing/objects.

`/health` checks process liveness. `/ready` checks DB connectivity and posts/users
tables within a deadline; it does not verify the full migration history or
external auth/storage/CDN services. Pool and DB operation timeouts are bounded.
See [release evidence](PHASE_10_REPORT.md) and the
[operational runbook](DEPLOYMENT_RUNBOOK.md).
