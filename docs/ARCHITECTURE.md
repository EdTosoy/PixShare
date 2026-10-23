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
                                        LocalStorage → /uploads
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
   The original URL remains the database reference.
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
allocations. No queue, cloud processor, or new backend dependency is required.
`Storage.describe()` returns optional metadata; reads never trigger generation.
Malformed/missing bundles and legacy records fall back to the original. The
explicit row-locked `scripts.backfill_variants` command optimizes compatible old
uploads without changing database rows. See [image/API details](IMAGE_DELIVERY.md).
`UPLOADS_DIR` is shared by the storage dependency, static mount,
and seed script. No S3 implementation exists yet; the old architecture doc's
claim that one existed was incorrect. The interface is ready for the adapter
specified in PRODUCTION.md.

## Frontend boundaries

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
Immutable versioned derivative URLs receive long-lived cache headers; original
URLs retain their existing behavior. No private-IP optimizer exception or
server-side remote image proxy is enabled. Typography uses installed system fonts so builds work
without a Google Fonts connection.

Caption-based image descriptions and card link names are normalized and bounded
to 160 characters, with neutral fallbacks instead of filenames. Redundant card
image alt text is empty because the enclosing link supplies the description.
Full captions and original filenames remain available on the detail page.
Automated axe scans complement actual keyboard/focus/error-state tests; they
do not establish complete accessibility conformance.
