# PixShare staging deployment plan

Prepared 2026-10-24. **Design: CONDITIONAL GO. Deployment: NO-GO until the
release gates and explicit infrastructure/budget approval are satisfied.**
This is a plan, not evidence that these accounts, resources or policies exist.
No commands in the cloud sections have been executed.

## Architecture and isolation

```mermaid
flowchart LR
  Browser -->|HTTPS / Clerk cookies| Vercel[Dedicated Vercel staging project]
  Browser -->|HTTPS / Bearer JWT| API[Render FastAPI / immutable image]
  Browser -->|Public HTTPS image reads| CDN[CloudFront / OAC]
  Vercel --> Clerk[Separate Clerk staging application]
  API --> Clerk
  API -->|Private network / TLS| PG[New Render PostgreSQL 17]
  API -->|OIDC role / signed SDK requests| S3[Private staging S3 bucket]
  CDN -->|Signed origin reads| S3
```

Use a new Render project/environment, Vercel project, database, bucket, IAM role,
Clerk application and two newly verified staging accounts. Start with an empty
database and storage namespace. Never import the local database, media,
Clerk users, browser states or Phase 10 restore fixtures. Synthetic smoke images
are created by the staging harness. Keep local filesystem development unchanged.

Recommended region pair: Render **Singapore**, S3 **ap-southeast-1**. Confirm
regional availability and final pricing before approval. Vercel serves the frontend
globally; place its server runtime near the API where supported. Media travels
directly from CloudFront to the browser, not through Vercel or Render. App/API/media
use stable sibling HTTPS hosts such as `app.stage.example.invalid`,
`api.stage.example.invalid`, `media.stage.example.invalid` (replace all examples).
Choose domains you control, never deploy these literal placeholders.

The existing responsive `<picture>`/WebP pipeline needs no Next image proxy or
wildcard image-host allowlist. `images.unoptimized` is intentional: the backend
already makes the variants. Object keys remain private internal references;
responses resolve them to the CDN origin. Keep the CloudFront **origin path empty**:
returned URLs already contain `pixshare/staging/...`.

## Budget for approval

USD/month, low traffic, one developer, estimates checked against current vendor
pages on 2026-10-24. No introductory credits assumed; taxes, domain registration,
support upgrades and unbounded traffic excluded.

| Resource | Proposed selection | Estimate |
| --- | --- | ---: |
| Vercel | Pro, one paid developer | $20 |
| Render workspace | Pro, enables AWS OIDC and isolated environments | $25 |
| API | `1c-2g`, 1 CPU / 2 GB, one instance | $25 |
| PostgreSQL | `0.5c-1g`, 1 GB RAM, 100 connections | $19 |
| PostgreSQL disk | 10 GB, conservative allowance at $0.30/GB | up to $3 |
| Clerk | Hobby within included usage | $0 |
| S3 + CloudFront | Planning allowance for 5 GB stored, 1,000 uploads, 100,000 reads, 20 GB delivery | $1–5 |
| **Planning total** | before overages and tax | **$93–97** |

The AWS allowance is a budget estimate, **not a regional price quote**. Price the
selected region, destinations, CDN plan, requests, historical versions, logs and
data transfer in the AWS calculator before approval. Media origin GETs and Render
outbound uploads can be charged separately. A larger image library or abuse can
exceed it. Existing accounts may already pay subscription fees: check incremental
costs rather than double-counting. Set AWS budget notifications, Render billing
alerts and Vercel spend controls before exposing staging. Alerts alone are not a
hard AWS spending cap.

[Render pricing](https://render.com/pricing),
[compute plan identifiers](https://render.com/docs/compute-plans),
[Vercel pricing](https://vercel.com/pricing),
[Clerk pricing](https://clerk.com/pricing),
[S3 pricing](https://aws.amazon.com/s3/pricing/),
[CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/).

Lower cost alternatives require a separate decision: Vercel Hobby is personal,
noncommercial only; Render Hobby lacks managed OIDC, requiring a tightly scoped,
rotated static server credential instead. The $7/512 MB API is not accepted without
image-decoding load evidence. Free Render web services spin down and free Postgres
expires after 30 days, lacks paid backup protections and is unsuitable for this
recovery exercise. Do not mistake a free workspace for free compute.
[Vercel terms](https://vercel.com/legal/terms),
[Render free limitations](https://render.com/docs/free).

## Manual configuration after approval

1. Confirm billing owners, monthly budget, region, domain ownership, registry and
   administrative MFA. Approve isolated staging resource creation explicitly.
2. Resolve the image vulnerability gate in `PHASE_11_REPORT.md`. Authorize logical
   checkpoint commits/publishing separately; this task authorizes neither.
3. Create a **separate Clerk application** and its production instance for staging.
   Configure the stable staging frontend domain and Clerk DNS records/certificates;
   enable actual email verification, allowed redirect destinations and intended
   signup policy. Obtain the matching live publishable/server keys privately.
   Existing production guards require live keys; do not set development mode to
   evade them. Create the two new users only through the staging signup flow.
4. Create empty paid PostgreSQL 17 and API resources in the same Render region.
   Disable external DB access (`ipAllowList: []`); use the private connection.
   Fill the reviewed template in `deploy/staging/render.yaml.example`. It is not
   an automatically applied Blueprint and contains no working credentials.
5. Create the isolated AWS resources and policies described below. Finish DNS/TLS
   for the CDN before uploading the first smoke image. API startup/readiness does
   not independently prove S3 or CloudFront availability.
6. Build once, scan, record and publish the approved API artifact by immutable
   digest. Set Render's image URL to that digest, registry read-only pull credential,
   environment, migration command, startup override and `/ready` health check.
7. Create a **dedicated Vercel project**, root directory `web`, Next.js, Node 24,
   pnpm 11.11.0, install `pnpm install --frozen-lockfile`, build `pnpm build`.
   Use this project's **Production environment for staging**, with a stable domain;
   do not reuse production's project or depend on random preview origins. Disable
   automatic Git deploys until an approved release pipeline exists. Configure secrets
   through its environment settings; no `vercel env pull` into tracked files.
8. Set exact origins everywhere, check HTTPS/cookies, execute the smoke sequence,
   record a baseline artifact, deploy a second compatible immutable release and
   rehearse rollback. Open broader staging access only after these gates pass.

### Render details

The API launch override is `/app/.venv/bin/python -m scripts.render_start`.
It binds `0.0.0.0:$PORT` (default 10000), retains concurrency 8, disables access
logs and preserves graceful shutdown. The adapter accepts Render's PostgreSQL URI
and translates its driver/TLS query for SQLAlchemy asyncpg without logging values.

**For both Alembic and API**, store `DATABASE_URL` already converted to
`postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require` (append with `&` if
another query parameter already exists).
Preserve percent encoding in passwords. Do this in a private editor/secret manager,
not terminal arguments/history. The predeploy command does not run the adapter.

Render's internal DB TLS uses a self-signed certificate and cannot use
`verify-full`. `ssl=require` encrypts but does **not authenticate the server's
certificate**; this is a documented private-network tradeoff requiring approval.
For an externally connected managed DB, require valid certificates and
`ssl=verify-full`; do not propagate the internal-network exception elsewhere.
[Render DB connection/TLS documentation](https://render.com/docs/postgresql-creating-connecting).

Run `/app/.venv/bin/alembic upgrade head` as the single predeploy migration job.
Inspect `alembic current`/`heads` first and record the revision. Use additive,
backward-compatible migrations; no seed import, destructive migration, legacy
backfill or automatic downgrade. This release adds no migration. Set at least
40 seconds shutdown grace around Uvicorn's 30 seconds.

Set `ALLOWED_HOSTS` to the custom API hostname **and the actual service
`onrender.com` hostname**. Render health probes use the verified custom hostname
when configured, otherwise the platform hostname. `/health` is process liveness;
`/ready` requires DB connectivity and tables within 3 seconds, returning generic
503 on failure. Neither probes object storage. No S3-backed staging disk is
required; `/app/uploads` is empty ephemeral legacy compatibility and `/tmp` must
be writable for bounded image processing. Measure RSS/concurrency under 16 MP
images before accepting capacity; one instance is not high availability.
[Render health checks](https://render.com/docs/health-checks),
[image deployment](https://render.com/docs/deploying-an-image).

Keep `FORWARDED_ALLOW_IPS` unset until the actual trusted ingress contract is
verified. Never set `*` merely to make peer-based rate limits work. The current
limiter is in-process and may share budgets across clients behind Render's proxy;
it is not a distributed abuse firewall. Vercel's WAF does not protect direct calls
to the Render API. Verify spoofed headers, real-client attribution and independent
client budgets before wider access; keep a small known tester group meanwhile.

### AWS permissions and CDN

Create a new unique `*-staging` bucket, Block Public Access **all four settings
on**, Object Ownership **bucket owner enforced** (ACLs disabled), SSE-S3 encryption,
versioning, and narrowly scoped lifecycle rules for old noncurrent versions and
abandoned multipart uploads. Review retention with backup policy; never expire
current live originals. Avoid SSE-KMS unless its extra IAM and charges are approved.

Use `deploy/staging/s3-runtime-policy.json.example` for the API role: Get/Put/Delete
only under `pixshare/staging/*`, ListBucket only for that prefix. No bucket creation,
ACL modification, policy changes, version deletion or unrelated bucket access.
Cleanup's bulk DeleteObjects uses the `s3:DeleteObject` permission. A separate
read-only verification role needs only scoped ListBucket/GetObject. Administrative
backup/version restore permissions belong to a separate operator role.

Prefer Render Pro managed AWS OIDC. Register the issuer
`https://oidc.render.com/WORKSPACE_ID`, audience `sts.amazonaws.com`, and use the
exact subject in `render-oidc-trust.json.example`:
`workspace:WORKSPACE_ID:environment:ENVIRONMENT_ID:service:SERVICE_ID`.
IDs come from the actual Render workspace/environment/service, never a wildcard.
Set `AWS_ROLE_ARN` in the API service. Render supplies
`AWS_WEB_IDENTITY_TOKEN_FILE`; do not invent a path or copy the token. Leave the
explicit `S3_ACCESS_KEY_ID`/secret/session fields unset so boto3 uses its default
web-identity chain. OIDC is not a private-registry pull credential. Validate role
refresh over a token expiry boundary after deployment.
[Render managed OIDC](https://render.com/docs/oidc).

Create CloudFront with the S3 REST origin (not website endpoint), **OAC signing
always on**, GET/HEAD only, viewer HTTPS redirect, TLS 1.2+, and a certificate in
us-east-1 for the custom CDN domain. Set its origin path empty. Apply the example
bucket policy **after substituting the exact distribution ARN**: read originals
and WebP variants only; manifests/listing stay private. No public writes, uploads,
presigning endpoint or browser AWS credentials. Confirm direct anonymous S3 reads
and CDN manifest reads return 403, while permitted image URLs return 200.
[AWS OAC guidance](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html).

Use cache headers already set by the application; content-address-independent
UUID groups make replacement URLs unique. Set short error cache TTL (e.g. 1s).
S3 CORS is unnecessary for normal `<img>`/`<picture>` display; enable only explicit
frontend GET/HEAD origins if a real browser fetch requirement is demonstrated.
CloudFront headers: correct image MIME, `nosniff`; do not apply a same-origin
resource policy that blocks the frontend's cross-origin images.

**Deletion limitation:** S3 deletion removes current origin objects after DB
commit, but public CDN/browser caches can retain an image for its one-year
immutable TTL. Versioning retains previous objects for recovery too. CDN 200 after
deletion is not evidence of a failed S3 cleanup. Immediate revocation requires an
approved invalidation/shorter caching policy and is not implemented here. Images
are public by product design; private bucket does not mean private gallery.

### Origins, authentication and headers

Exact HTTPS frontend origin goes in both backend CORS and authorized parties,
and frontend `CLERK_AUTHORIZED_PARTIES`. No wildcard, path, ephemeral preview
allowlist or localhost in production settings. API mutation Bearer tokens remain
required; backend owns authorization. Sibling domains help Clerk's secure cookie
flow; verify Secure, expected SameSite and logout invalidation in browser tools
without exporting cookie values. Do not force HttpOnly on Clerk cookies required
by its browser SDK or weaken cookie flags to work around redirects.

Existing CSP is a limited baseline (`frame-ancestors`, `base-uri`, `object-src`),
not a complete script/connect/image policy. Stage a stricter policy in
**Report-Only** after observing actual Clerk, API and CDN hosts; permit necessary
Clerk frames/connections and preview `blob:` images. Do not claim an untested
nonce policy works. Preserve focus, responsive and theme behavior. Verify HTTPS
redirects/HSTS supplied by each provider; enable subdomain-wide HSTS only after
all required subdomains support HTTPS. `X-Frame-Options: DENY` remains intentional.

If Vercel Deployment Protection is enabled, first verify the plan includes the
needed policy. The provided harness does not bypass it; use an explicitly reviewed
origin-scoped automation mechanism or record a blocked result. Never set a global
Playwright bypass header (it would be sent to Clerk/API/media) or put a secret in
a URL. API and public CDN remain separately reachable, even if Vercel is protected.

## Environment and secrets checklist (names only)

| Target | Required configuration names |
| --- | --- |
| API | `ENVIRONMENT`, `DATABASE_URL`, `UPLOADS_DIR`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `CLERK_AUTHORIZED_PARTIES`, `CLERK_SECRET_KEY` (or reviewed `CLERK_JWT_KEY`), `STORAGE_PROVIDER`, `S3_BUCKET`, `S3_PREFIX`, `S3_REGION`, `S3_PUBLIC_BASE_URL`, `AWS_ROLE_ARN` |
| API bounds | `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_TIMEOUT`, `DATABASE_COMMAND_TIMEOUT`, `READINESS_TIMEOUT`, `API_MAX_BODY_BYTES`, `REQUEST_BODY_TIMEOUT`, `API_READ_LIMIT`, `API_WRITE_LIMIT`, `S3_CONNECT_TIMEOUT`, `S3_READ_TIMEOUT`, `S3_MAX_ATTEMPTS` |
| Frontend build | `PIXSHARE_ENVIRONMENT`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_CLERK_SIGN_IN_URL`, `NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL`, `NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL` |
| Frontend server | `CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES`, same publishable key and environment as build |
| Provider-injected | `PORT`, `AWS_WEB_IDENTITY_TOKEN_FILE` |
| Operators / CI, if used | `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `RENDER_API_KEY`, `RENDER_SERVICE_ID`, `GHCR_TOKEN`, `AWS_PROFILE` |
| Optional static-credential alternative | `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_SESSION_TOKEN` (never together with an accidentally overriding stale credential set) |
| Smoke runner, no keys | `STAGING_WEB_URL`, `STAGING_API_URL`, `STAGING_MEDIA_URL` |

Defaults are documented in `.env.production.example`; use 5 pool + 5 overflow,
3s readiness, 10 MiB file / 11 MiB envelope, 30s body deadline, 300 reads/60 writes
per peer per minute, S3 connect 3s/read 10s/3 attempts initially. Keep `S3_ENDPOINT_URL`
unset for AWS. No AWS, database or Clerk server credential has a `NEXT_PUBLIC_` name.
Public build values are baked in: updating runtime settings alone does not change
the browser's API URL or publishable key. Redeploy after approved changes.

## Release, deployment and rollback commands

**After approval only**, from the approved clean checkpoint; do not run these
cloud commands during preparation. Configure CLI logins interactively/secret
stores; never embed tokens/passwords in arguments. Commands with placeholders
require operator substitution and review.

```sh
# Local immutable candidate, build once. RELEASE is the full approved commit SHA.
RELEASE=$(git rev-parse HEAD)
docker build --platform linux/amd64 -f dockerfile \
  --label org.opencontainers.image.revision="$RELEASE" \
  -t "ghcr.io/OWNER/pixshare-api:$RELEASE" .
# Scan the BUILT image, archive JSON/SBOM privately, triage before publishing.
trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 \
  "ghcr.io/OWNER/pixshare-api:$RELEASE"
# Publishing requires separate authorization; authenticate via credential helper.
docker push "ghcr.io/OWNER/pixshare-api:$RELEASE"
docker buildx imagetools inspect "ghcr.io/OWNER/pixshare-api:$RELEASE"
# Record registry sha256 manifest digest, not local image ID or mutable tag.
```

Set the Render image to `ghcr.io/OWNER/pixshare-api@sha256:APPROVED_DIGEST` in
its dashboard, review the predeploy result and deploy manually. The template can
be validated **after placeholders are replaced** using `render blueprints validate
PATH` (confirm with installed CLI help); validation is not creation approval.

```sh
# From web/, after the dedicated project/env are configured and approval granted:
vercel --prod
# Record the immutable deployment URL/ID and associated source/env configuration.
vercel inspect APPROVED_DEPLOYMENT_URL
# Later rollback to the previously VERIFIED artifact, never rebuild it:
vercel rollback PREVIOUS_VERIFIED_DEPLOYMENT_URL
```

Retain at least two API **registry digests** and Vercel deployment IDs, lockfiles,
source commit, scan/DB revision/configuration version, public build inputs,
timestamp/operator and smoke result. Secrets belong in the secret manager, not
the release manifest. Never use `latest`. Vercel's deployment is the frontend
rollback artifact; the local frontend Docker image is an alternative runtime,
not the artifact Vercel actually runs.

Render rollback: pause writes if compatibility is uncertain, select the previous
verified image digest, preserve compatible DB/env, deploy and wait for `/ready`;
then run `persistence`. Use the dashboard's restart to rehearse container recovery,
record deployment/event IDs and downtime; do not recreate the DB or bucket.
If a migration breaks backward compatibility, stop and use the recovery runbook;
never automatically downgrade the database. **HEAD `632b15c` is not an eligible
S3 rollback target**: it predates the current storage references. First establish
two S3-compatible verified artifacts. A first deployment cannot claim a rollback
rehearsal until a second compatible release exists.
[Vercel rollback](https://vercel.com/docs/instant-rollback).

## Executable smoke sequence and recording

Install the locked frontend dependencies and Playwright Chromium locally. The
new runner intentionally does not load `.env.local`/`.env.e2e.local`, import the
development auth suite or use Clerk testing tokens/OTP shortcuts. It never prints
raw browser exceptions, tokens or request bodies. Storage states/reports/checkpoint
are private under ignored `web/staging-artifacts/` (directory 0700, files 0600).
They are bound to the three configured origins; do not reuse elsewhere or publish
them. Expired sessions require fresh real login; bootstrap requires new accounts,
so retain states during the rehearsal and restart a fresh isolated smoke run if
they expire. Keep accounts afterward unless separately authorized to delete them.

```sh
cd web
export STAGING_WEB_URL=https://app.stage.YOUR_DOMAIN
export STAGING_API_URL=https://api.stage.YOUR_DOMAIN
export STAGING_MEDIA_URL=https://media.stage.YOUR_DOMAIN
node scripts/staging-smoke.mjs public --approved-staging
node scripts/staging-smoke.mjs bootstrap-owner --approved-staging
node scripts/staging-smoke.mjs bootstrap-other --approved-staging
node scripts/staging-smoke.mjs crud --approved-staging
# From repository root, read-only AWS operator session for the NEW bucket:
cd ..
uv run python -m scripts.check_staging_cleanup --bucket YOUR_BUCKET-staging \
  --checkpoint web/staging-artifacts/checkpoint.json --after-replacement
# From web/, once BEFORE and again AFTER each approved Render restart / rollback:
cd web
node scripts/staging-smoke.mjs persistence --approved-staging
# After all persistence/restart/rollback observations:
node scripts/staging-smoke.mjs cleanup --approved-staging
# From repository root:
cd ..
uv run python -m scripts.check_staging_cleanup --bucket YOUR_BUCKET-staging \
  --checkpoint web/staging-artifacts/checkpoint.json
```

| Acceptance item | Evidence / required measurement |
| --- | --- |
| Public HTTPS | `public`: health/ready/posts 200, unauthenticated `/users/me` 401, exact CORS, landing/Explore at 1440/768/390 without overflow; separately verify HTTP redirects and hostile-origin preflight |
| Signup/signin/logout | Both headed bootstrap sessions use actual Clerk UI and real email verification; logout removes session and protects My Gallery, signin reaches authenticated API 200; no development helper |
| Upload + variants | `crud`: UI POST 201, CDN original in exact staging namespace, nonempty variants, loaded `currentSrc` matches a variant, MIME WebP; byte count and original SHA-256 saved |
| Edit + replace | UI caption update, replacement PATCH 200, new immutable media URL; first group absent at S3 origin using read-only cleanup checker |
| Ownership | Distinct backend identities; other account lacks edit action, real PATCH/DELETE 403, owner's data unchanged |
| DB persistence / restart | Same checkpoint row, full post metadata and media hash before/after Render restart; `/ready` returns 200; save operator event/time, observation interval and recovery duration |
| Rollback | Same checks after switching to the previous verified API digest and Vercel deployment; record both provider artifact IDs, migration revision, config version and downtime separately |
| Delete + storage cleanup | UI delete + post 404; read-only ListObjectsV2 proves BOTH exact created groups absent, independent of CDN cache; version history remains intentionally |

The harness does not restart services, deploy, provision, backfill, migrate, delete
accounts or delete unknown posts. `crud` deliberately retains one smoke post for
the persistence rehearsal. It reserves a checkpoint before upload; failures retain
it for review. If a network failure prevents receiving the upload ID, inspect only
the dedicated user's uniquely captioned smoke post; never run broad cleanup.
Run commands sequentially. A partial CRUD run is not a pass or safe to overwrite.

Record each run in a **private** release manifest: command, UTC time, PASS/FAIL/
BLOCKED, provider artifact IDs, migration revision, restart/rollback event IDs,
elapsed recovery time and report filenames/hashes. No email addresses, JWTs,
passwords, browser storage, private connection URLs or raw HAR/traces in docs.
The current harness guards and syntax were locally checked; **hosted execution
and these acceptance results remain NOT RUN until infrastructure approval**.

## Operations, backup and recovery

Poll `/ready` and the frontend over HTTPS; alert on sustained 503/5xx, 401 spikes,
429 rates, upload failure/variant fallback warnings, RSS/CPU, DB pool saturation,
disk/connection limits, S3 errors and budget thresholds. Use Render/Vercel native
metrics initially; additional monitoring services require budget approval. Set
log retention, restrict operator access, keep access logs off and never enable
SQL parameter, JWT/cookie, SDK debug or environment dumping. Scrub incident exports.

Paid Render PG has PITR (3 days on Hobby workspace / 7 days on Pro). Restore creates
a **new billable instance**: obtain approval, restore into a new isolated target,
verify Alembic/table checks and checkpoint hashes, then explicitly switch the
connection secret. Do not restore over a live database. Maintain encrypted logical
exports in a separate protected backup location with restore-only operator access;
coordinate DB and S3 versions with paused writes, retaining manifest/version IDs.
Set a proposed staging RPO 24h / RTO 1h, **targets unverified until rehearsal**.
[Render backups](https://render.com/docs/postgresql-backups).

Use `docs/DEPLOYMENT_RUNBOOK.md` for coordinated recovery and orphan handling.
Reconciliation is dry-run first; apply only under separately approved paused writes
and reviewed age/namespace. No optional legacy backfill. Old object versions/CDN
cache are not immediately purged by post deletion. Do not enable cleanup automation
until backup/retention and outage recovery are exercised on this new environment.
