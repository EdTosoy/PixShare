# Phase 10 — Production readiness and security audit

Date: 2026-10-24. Scope: existing MVP plus the uncommitted Phase 9 storage work.
No commits, pushes, deployments, destructive migrations, paid provisioning or
live cloud changes were performed. Existing data, uploads and verified Clerk
accounts were preserved. All recovery targets are isolated local fixtures.

## 1. Executive summary

**Recommendation: CONDITIONAL GO as a release candidate for staging. Public
production traffic is NO-GO until every hard gate in section 10 is satisfied.**
The application-level repairs and local checks are evidence for a candidate,
not certification of untested AWS, production Clerk, TLS, DNS, backup services or
operational capacity.

The audit found known vulnerable language packages, insufficient production
configuration guards, unbounded multipart input before file validation, ambient
cookie acceptance in a Bearer API, no rate limiter and liveness-only health
checks. Focused changes address these findings while retaining the established
UI, API contracts, ownership locks, original images and local/S3 providers.

Coordinated backup/restore succeeded into separate PostgreSQL/MinIO containers
and a fresh filesystem. Identifiers, owner mappings, references and bytes matched.
Database/storage outage recovery was exercised without stopping the original
test services or touching application data. Practical operator instructions are
in [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md).

## 2. Security findings and remediation

Severity reflects plausible impact; a package advisory is not proof that its
vulnerable feature was reachable through PixShare.

| ID / severity | Finding | Remediation / evidence |
| --- | --- | --- |
| SEC-01 / Critical | Locked dependencies included critical Next.js advisories and vulnerable image/JWT/crypto packages | Next/eslint-config-next 16.4.1; Pillow 13.0.0; Clerk Python 7.0.0 to permit patched cryptography 50.0.2; PyJWT 2.15.1, certifi 2026.10.23, urllib3 2.8.0; Zod 4.6.6; patched compatible build/lint overrides. Language-package audits now report zero findings |
| SEC-02 / High | Production startup did not require live auth configuration, exact HTTPS origins or API hosts; an empty authorized-party list could deploy an unusable API | Production settings fail closed; require live secret or trusted JWT public key, explicit HTTPS CORS/authorized origins and API hostnames; reject development keys, wildcard origins and common loopback defaults. Environment names are constrained. Frontend production guards require HTTPS API/live key shapes and explicit authorized parties |
| SEC-03 / High | File limits ran after multipart parsing, allowing larger file parts to consume spool resources before rejection | ASGI guard counts the complete raw body before multipart parsing, rejects >11 MiB including unknown/understated lengths, and bounds body receipt to 30s; existing 10 MiB file/16 MP/20,000px validation remains. Chunked, false-header and slow-body tests pass |
| SEC-04 / High | Optional HTTPBearer allowed the Clerk SDK to consider ambient session cookies on API mutations | Require explicit Bearer credentials before SDK verification. A genuinely signed cookie-only JWT is rejected while the same Bearer JWT succeeds. Ownership checks remain inside locked backend mutations |
| SEC-05 / Medium | No application abuse budget | Bounded per-peer read/write minute windows, 429 + Retry-After, 10,000-entry LRU cap, independent read/write quotas. Spoofed raw X-Forwarded-For does not change the peer. Global/shared ingress limits remain a production gate |
| SEC-06 / Medium | Process liveness could report healthy with an unavailable/unmigrated DB | `/ready` checks DB/table access within a deadline; `/health` remains liveness. Actual isolated DB outage: ready 503 in 0.01s, health 200; readiness recovered after restart |
| SEC-07 / Medium | No baseline browser security headers | Web responses have nosniff, anti-framing, referrer/permissions policies and CSP base/object/frame-ancestor restrictions; remove X-Powered-By. HTTP assertions pass. Full nonce-based script/connect CSP remains deployment-specific |
| SEC-08 / Medium | Development Compose and floating runtime tooling were unsuitable as a production procedure | Separate production Compose example: no automatic migrations/database provisioning; existing legacy volume, nonroot images, read-only rootfs, tmpfs, resource/log bounds, readiness health check and private loopback ports. uv image pinned to 0.11.21; production image digest/OS scan gates remain |
| SEC-09 / Low | Operational artifacts lacked broad ignore coverage | Ignore private envs, AWS credentials, backups/dumps/logs/key files and caches. Preserve explicit env examples and intentional SQL initialization script. Docker contexts exclude operational material |

### Dependency audit scope

Initial `pip-audit`: **60 findings across five runtime packages**, representing
57 unique advisory IDs (cryptography entries were duplicated across dependency
metadata). Initial `pnpm audit`: **23 findings**: 5 critical, 10 high, 7 moderate,
1 low. A follow-up registry response also reported a high Zod advisory; it was
patched before final verification. These are scanner results, not 60 reproduced
application exploits.

Final Python runtime export and complete npm lock audit: **zero known
vulnerabilities reported**. Security floors are recorded in uv constraints;
three pnpm overrides update compatible brace-expansion 1.x, js-yaml 4.x and
source-map-js 1.x dependencies. Existing lockfiles were updated normally; no
migration history or product framework was replaced.

The Python audit exports the locked non-dev environment, uses `pip-audit` with
`--no-deps --disable-pip`, and does not claim coverage of development-only Python
tools. npm includes development dependencies. Neither audit scans container OS
packages, arbitrary native libraries, browser images or future advisories. Image
SBOM/CVE scans and renewed audits are required before publishing/deploying.

### Additional inspected boundaries

- Clerk SDK verifies RS256 signatures, time claims and authorized parties;
  `accepts_token=["session_token"]` excludes machine/API token classes. Trusted
  JWT public keys or secret-authenticated instance JWKS bind verification keys.
  SDK `_decode_token` uses a fresh options dictionary per call; no application
  path reuses an unverified decoding-options object. Wrong signatures, expiration
  and wrong origins are tested. Raw tokens/settings/SDK diagnostics are not logged.
- `sub` must be a nonempty bounded string; local identity creation tolerates its
  unique-insert race. User gallery IDs cannot be selected by the caller. PATCH/
  DELETE enforce owner equality and retain row locks. Authentication/ownership
  was also checked with two distinct real Clerk development accounts.
- Upload MIME/format, decoded dimensions, decompression warnings and bytes remain
  validated before storage. Pillow warnings were not disabled. Originals remain
  unchanged; bounded variants preserve dimensions/orientation/alpha behavior.
- Local deletion rejects traversal/foreign references and handles symlinks
  conservatively. S3 deletion accepts only the configured bucket/prefix and
  canonical group/original format. Conditional original PUT prevents collisions;
  ambiguous writes are cleaned only when operation ownership can be established.
- S3 credentials remain server-side. Local service policy tests deny anonymous
  writes, deletes, listing and manifest reads while permitting image GET.
  Runtime AWS least-privilege roles and CDN origin access have **not** been tested
  on AWS; local integration uses dedicated fixture administration credentials.
- SQL parameters are hidden; database/storage responses are generic. Settings
  repr excludes the database URL and Clerk secret. API container access logging
  is disabled by default; ingress must provide sanitized operational logs.

## 3. Authentication readiness and Clerk warnings

Three different messages must not be conflated:

1. Clerk's development-instance telemetry notice is expected development output.
   No warning-suppression or auth bypass was added.
2. `[Clerk Testing] FAPI request failed after 4 attempts ... Unexpected token '<'`
   was reproduced in WebKit. Installed `@clerk/testing` routes every FAPI request
   through `route.fetch()`, follows redirects, then unconditionally calls
   `response.json()`. `/v1/client/handshake` is a **browser navigation**, whose
   redirect can end at application HTML and whose Set-Cookie flow belongs in the
   browser. The test-only `prepareClerkBrowser()` now passes real handshake
   navigations directly to the browser, preserving the official testing token;
   JSON API calls retain the SDK helper. No application authentication is mocked.
3. The server's generic `Refreshing the session token resulted in an infinite
   redirect loop ... keys do not match` message is not a reliable mismatch
   diagnosis. A private, in-memory SDK diagnostic reproduced
   `dev-browser-missing`, `session-token-missing` and transient
   `session-token-but-no-client-uat`. The SDK emits that generic message when its
   two-second redirect counter reaches three. Configured secret/publishable keys
   were compared privately and matched. No credentials were changed.

The initial WebKit CRUD reproduction failed at sign-out navigation; fixing the
JSON interception removed its JSON warnings but exposed the separate navigation
race. Waiting for the actual sign-out document load and using the real My Gallery
link fixed the focused workflow (**2/2 including setup**). Development cookie
handoff warnings can still occur; they are not certified harmless for production.
There is no evidence here of a production key mismatch, because production keys/
domains were not available or exercised. The final canonical-host server log still
contained 44 generic redirect-loop warnings across the final browser runs, while
all 47 checks passed. The JSON-interception warning did not recur in the final
WebKit run. These counts do not establish that production renewal is safe.

Production requires live keys, canonical HTTPS domains, DNS/certificates,
redirect/OAuth configuration, both SDKs' authorized parties, and a real session
renewal/sign-out test across browsers. See the runbook. Development users remain
intact; production identities have different Clerk IDs. No user migration or
ownership reassignment was performed. An existing-data identity migration, if
needed, is a separate approved release gate.

## 4. Infrastructure architecture

```text
Browser ──HTTPS ingress── Next.js
       └─HTTPS ingress── FastAPI ──private TLS── PostgreSQL
       └─public CDN GET──────────── private S3 origin
                              FastAPI ──IAM/SigV4── S3
Legacy image GET ── FastAPI /uploads ── retained persistent volume
```

Storage references stay durable; public base/CDN URLs resolve at response time.
Both local and S3 images remain supported. No automatic migration/backfill runs.
Runtime roles need prefix-constrained ListBucket plus Get/Put/DeleteObject, not
bucket administration. CDN reads must not expose private manifests. User writes
still pass through the API's Bearer/ownership checks.

Readiness certifies DB/table access only, not Clerk, all schema revisions, S3,
CDN, DNS or backups. DB pool/acquisition/command timeouts and per-request body
limits are bounded. Per-worker raster limits do not establish aggregate capacity;
perform staging load tests with the intended workers, network and image mix.

## 5. Required production environment

[`.env.production.example`](../.env.production.example) contains placeholders
only; [the runbook](DEPLOYMENT_RUNBOOK.md#2-prepare-configuration-privately)
explains ownership and injection. Never copy its placeholders into a live service.

| Scope | Required settings |
| --- | --- |
| API | `ENVIRONMENT=production`, private `DATABASE_URL`, `ALLOWED_HOSTS`, explicit HTTPS `CORS_ORIGINS` / `CLERK_AUTHORIZED_PARTIES`, live Clerk secret or trusted JWT PEM, persistent `UPLOADS_DIR` |
| S3 API | Provider/bucket/prefix/region/public base; optional HTTPS compatible endpoint/addressing; prefer IAM role, optional paired server-only credentials/session token |
| Web build | `PIXSHARE_ENVIRONMENT=production`, HTTPS `NEXT_PUBLIC_API_URL`, live `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` |
| Web runtime | Matching live Clerk secret, publishable key and exact authorized parties; no S3/database secrets |
| Operations | Immutable image references, existing uploads volume, restricted ingress proxy IPs, secret versions, timeout/pool/resource settings, monitoring and backup destinations |

Public frontend values require rebuilding the image. Runtime-only changes cannot
repair a frontend compiled for another API/Clerk instance. The production Compose
example was syntax-validated with placeholders; it was **not deployed**.

## 6. Repository, CI/CD and checkpoint strategy

Audit began on main at `632b15c` with **19 modified tracked files and 11 untracked
Phase 9 entries**, not a clean tree. That work was preserved. Recent history also
includes merge `2edca2c` and seed work `fc7b249`; no Git history was rewritten.

A pattern scan of all locally reachable Git history inspected **285 text blobs**
and found zero candidate Clerk secrets, AWS access keys or private-key blocks.
Changed files and emitted browser bundles were also checked against configured
private values without printing them. This is bounded pattern/value evidence,
not an exhaustive proof that every historic binary or revoked credential is safe.
No remote secret-scanning service was invoked.

Never commit working `.env*`, `.aws/`, JWTs/PEM private keys, database backups,
user uploads, generated test/Next outputs, authenticated traces/error contexts or
private reconciliation reports. Intentional tracked exceptions include empty-key
env examples, `docker/postgres/init.sql` (a database-initialization statement, not
a dump), bundled demo media and reviewed UX documentation assets. Review their
privacy/licensing separately before external publication.

Recommended future authorized checkpoints:

1. **Phase 9 storage foundation:** adapters, lifecycle tests, configuration and
   storage docs. Select overlapping hunks carefully rather than staging all work.
2. **Phase 10 security candidate:** patched dependencies/locks, request/auth/
   configuration guards, readiness, headers and security regression tests.
3. **Operations evidence:** production examples, CI hardening, runbooks and final
   verification report. Bind these artifacts to the reviewed candidate revision.

No checkpoint was created or pushed during this task. Existing workflows now use
read-only repository tokens. Public web CI explicitly selects public projects and
waits for `/ready`; it does not misrepresent skipped hosted auth as coverage.
A protected release workflow should additionally require the real local S3 job,
all three browser engines with dedicated development secrets, dependency/image
scans and approval gates. Do not expose secrets to fork PR jobs. Hosted CI and
registry publishing were not executed; configure protected environments and
required checks before a public release.

## 7. Backup, recovery and rollback

With the source audit API stopped, the local drill captured a custom-format
PostgreSQL dump, full legacy media archive, all S3 objects/private manifests and
checksum inventory. Restore used a fresh PostgreSQL container on 55440, separate
MinIO on 59001 and a fresh media directory. Nothing was restored over originals.

Verified: **4 posts, 3 user mappings, 13 local files, 6 S3 objects**, equal IDs/
owner references/content hashes. The nonroot, read-only API image then served
readiness, four posts and **16 media GETs** from the restored targets.

Stopping only restored PostgreSQL produced `/ready` 503 in **0.01s**, with
`/health` still 200. Restart restored readiness/data. Stopping only restored
MinIO produced a sanitized SDK upload failure in **0.39s** under the fixture's
two-attempt policy; public rows/original URLs remained, optional metadata fell
back, and all six object hashes matched after restart.

Commit-failure rollback, partial publication/deletion, original preservation,
legacy compatibility and orphan audit/apply behavior are also included in the
real local S3 regression cases. No orphan sweep or optional backfill ran against
user data. S3 cleanup is not atomic with PostgreSQL and can leave orphans; review
private inventories and pause/drain writers before applying cleanup.

No destructive migration was introduced. Fresh databases reached existing head
`cdae1ace538f` using both existing revisions. Rollback must use a security-patched
S3-capable image and preserve data/configuration. **Phase 8 main `632b15c` is not
a safe rollback target once S3 references exist.** No compatible published
rollback artifact was created; establishing one is a hard gate.

Managed PITR, restore credentials, offsite retention, regional failover and
production RPO/RTO have not been verified. The runbook's RPO/RTO are proposed
targets, not measured production guarantees.

## 8. Verification results

| Check | Final result / scope |
| --- | --- |
| Backend `uv run pytest -q` with explicit local S3 opt-in | **PASS — 129 passed, 0 failed, 0 skipped**, 18.28s |
| Real local S3 cases | **PASS — 14 cases**, included in backend total; per-test owned namespaces, no successful S3 mocks |
| Ruff | **PASS**, no findings |
| basedpyright | **PASS**, 0 errors / 0 warnings |
| Frontend ESLint / TypeScript | **PASS / PASS** |
| Next.js 16.4.1 production build | **PASS**; development Clerk credentials, latest isolated build targets API 8109 |
| Chromium final canonical-port suite | **PASS — 24 passed, 0 failed, 0 skipped**, 2.9m; desktop/tablet/mobile, public/real Clerk workflows |
| Firefox/WebKit final canonical-port suite | **PASS — 23 passed, 0 failed, 0 skipped**, 3.9m; 11 scenarios per engine plus setup |
| Accessibility | **PASS** within all three engine suites: axe A/AA/best-practice plus keyboard/dialog/theme/reduced-motion; no observed violations under the tested rules |
| Python runtime audit / npm lock audit | **PASS / PASS — 0 reported findings** after patching; OS/native image scan not run |
| Production config negative checks | **PASS**; unsafe API configs rejected; frontend refuses HTTP/development-key production build inputs |
| Baseline web HTTP headers / bundle-secret scan | **PASS / PASS** |
| Git history / changed-file privacy review | **PASS**, bounded scan scope described above |
| Production Compose syntax | **PASS**, placeholders only, no production services started |
| API Docker image build / nonroot read-only recovery smoke | **PASS / PASS**; four restored posts + 16 media GETs |
| Coordinated DB/local/S3 backup/restore | **PASS**; exact counts/hashes in section 7 |
| Actual isolated DB and S3 outage/restart | **PASS**; readiness/liveness separation, safe upload failure, metadata fallback and unchanged recovered objects |
| Fresh DB migrations | **PASS**, existing two revisions to `cdae1ace538f`; no downgrade |
| Production infrastructure / live Clerk / native Safari / hosted CI | **NOT RUN**, no such deployment authorized or available |

Backend command selected `pix_share_phase10_test` and an ignored local S3 env
file, with `S3_INTEGRATION_TEST=1`. Backend unit cases retain existing test
fixtures; signed-JWT cases use the real Clerk SDK with ephemeral trusted RSA
keys, and hosted browser cases use genuine dedicated Clerk development users.
No product authentication bypass or disabled security check was introduced.
Independent backend cases reset only the per-process rate-window state.

Final browser configuration: frontend `http://localhost:3109`, API
`http://localhost:8109`, with matching CORS/authorized parties supplied only to
these test processes. The Playwright container matches 1.64.1 and supplies
Firefox 157.0 / WebKit 27.2. The host Chromium sandbox remains enabled.

**Earlier failed/invalid attempts are not hidden:** an initial backend run had
127 passes and one readiness-test failure because the test tried to patch a
read-only engine instance method; class-level fault injection fixed that fixture
and the complete suite passed. WebKit warning reproductions were 1 pass/1 fail
before the repairs, 1 pass/1 fail after the JSON-only repair, then 2/2 after the
sign-out navigation repair. An early Chromium run passed 24/24 on port 3000.
A cross-browser run was then aborted when it reached another local application
on that port; those results are invalid as PixShare evidence. An isolated-port
attempt using a mismatched literal bind hostname also timed out and was stopped.
Using the canonical localhost bind and verifying application identity from both
host and container resolved the environment setup; final suites use only the
dedicated canonical ports. The unrelated application was not changed.

The Nix workstation requires its GCC library path for Python extensions and the
Nix loader for the locked Ruff binary. Direct installed-tool executions were the
equivalent of `uv run ruff check .` and `uv run basedpyright`. Initial pnpm store
path and diagnostic bind-mount issues were resolved without changing project
functionality or global user configuration.

## 9. Remaining risks

- Actual production Clerk, DNS/TLS, issuer/domain/cookie behavior and identity/data
  transition are unverified. Development cookie handoff warnings remain observed.
- AWS IAM, bucket public-access policy, CloudFront/OAC, encryption, versioning,
  retention, restore and takedown/cache invalidation are unverified on AWS.
- No container OS/native-library SBOM/CVE scan, sustained load test, real ingress
  global rate-limit test, operational alert exercise or hosted release CI run.
- No safe published rollback artifact; the old Phase 8 image cannot read S3 refs.
- No durable media cleanup outbox or create idempotency key. Failures can leave
  orphans; a committed mutation followed by response failure must not be blindly
  retried. Reconciler apply can partially complete before an error.
- Namespace orphan scans and per-post S3 metadata reads have costs/latency that
  must be measured with the real dataset/vendor. Per-request SDK retry budgets
  are not an end-to-end list-response deadline.
- Public media/cache retention and original EXIF/GPS require an approved privacy/
  retention policy. Versioned buckets retain bytes beyond normal delete markers.
- The per-process limiter is a fallback, not shared global protection. Current
  resource bounds are starting settings, not a capacity or denial-of-service SLA.
- ESLint 9 emitted an upstream unsupported-version warning during installation.
  It is development tooling and the npm audit reported no known vulnerabilities;
  plan its supported-version migration separately rather than hiding the notice.
- Full script/connect CSP, native Safari/physical-device behavior and complete
  WCAG conformance are not established by these local browser tests.

## 10. Deployment checklist and go/no-go criteria

All hard gates below must be evidenced before public production traffic:

- [ ] Authorized checkpoint commits; reviewed diff/privacy evidence; immutable,
      security-scanned API/web images tied to the tested revision.
- [ ] Zero unaccepted applicable critical/high dependency and image findings;
      renew scans immediately before release.
- [ ] Live matching Clerk configuration, canonical domains/certificates, exact
      origins and successful multi-browser renewal/sign-out/ownership smoke tests.
- [ ] Approved existing-data/identity transition; preserve development users/data;
      no implicit reassignment or destructive migration.
- [ ] Actual private DB/S3/CDN IAM/TLS/public-read/anonymous-denial policies tested;
      legacy volume present and backups configured.
- [ ] Shared ingress body/rate/concurrency limits, trusted proxy handling, HTTPS,
      logging redaction, resource capacity and alerts verified.
- [ ] Coordinated production-equivalent backup restored in isolation; owner,
      encrypted/offsite retention and agreed RPO/RTO evidenced.
- [ ] S3-capable, security-patched rollback artifact and maintenance/cutover plan
      tested; migration head/compatibility reviewed.
- [ ] Final backend/storage, frontend/build, Chromium/Firefox/WebKit and
      accessibility checks pass on staging with no unexplained failures/skips.
- [ ] Explicit deployment approval obtained. This audit grants none.

**GO** only after every hard gate passes. **CONDITIONAL GO** currently means the
candidate may proceed to reviewed staging verification. Any failed auth/ownership,
secret exposure, unexplained critical/high vulnerability, missing coordinated
backup or incompatible rollback image is an immediate **NO-GO** for public launch.

## Primary sources and evidence

- [Next.js image-optimization advisory / patched 16.4.1](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw).
- [Pillow 13 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html).
- [Clerk production deployment and authorized parties](https://clerk.com/docs/guides/development/deployment/production).
- [Clerk authenticateRequest contract](https://clerk.com/docs/reference/backend/authenticate-request).
- [Clerk handshake flow](https://clerk.com/docs/guides/how-clerk-works/overview#the-handshake).
- [Starlette request/form parsing limits](https://www.starlette.io/requests/).
- Installed Next 16.4.1 header/config docs, installed Clerk Python 7.0.0 verification
  code and installed JS SDK/testing source maps were inspected. Installed
  Starlette 1.4.1 lacks the newer documentation's body-limit middleware, so a
  focused ASGI guard was implemented instead of importing an unavailable API.
- Detailed audit JSON, private backup/inventories and diagnostic logs remain
  under `/tmp/pixshare-phase10`; private env files are ignored and mode 0600.
  Do not publish those artifacts without a separate privacy review.

## Retained local artifacts and final state

Verification frontend/API processes and the three Phase 10 restore containers
were stopped after the checks. Restore volumes, the private dump/media/object
inventory and ignored mode-0600 test environment files were retained for review.
The pre-existing local PostgreSQL and Phase 9 MinIO test services were left as
found. Root `.env`, web Clerk configuration, existing uploads/accounts and
unrelated applications were not changed. No optional backfill or live-data
cleanup was performed. Production setup remains an operator/approval task.
