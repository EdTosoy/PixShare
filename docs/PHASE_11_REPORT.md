# Phase 11 — Staging deployment preparation

Date: 2026-10-24. Baseline: HEAD `632b15c`, plus existing uncommitted Phase 9/10
work. Source of truth: `PHASE_10_REPORT.md` and `DEPLOYMENT_RUNBOOK.md`, supplemented
by current official provider documentation linked in `STAGING_DEPLOYMENT_PLAN.md`.

## Assessment

**CONDITIONAL GO for the proposed architecture. NO-GO for deploying the current
images until the unresolved image security gate is triaged/approved and the owner
authorizes infrastructure and spending.** This is a stricter image gate than the
previous phase: actual container scanning discovered OS/tool findings outside
the earlier language-package audit's scope. It does not invalidate the recorded
application tests or establish that those OS findings are remotely exploitable.

Vercel frontend + Render container + managed PostgreSQL + AWS S3 + Clerk is
compatible, with four important qualifications:

1. Add **CloudFront with Origin Access Control** for public image reads from a
   private S3 bucket. A private bucket alone cannot supply the existing public URLs.
2. Render needs its port and PostgreSQL driver/TLS conventions configured correctly.
   A new launch adapter handles runtime conversion without changing local startup.
3. Strict staging settings require **a separate Clerk application's production
   instance**, matching live keys and verified domains. The existing development
   auth suite intentionally refuses live keys; use the new real-session harness.
4. Prefer Render Pro AWS OIDC rather than long-lived S3 credentials. This adds a
   workspace charge; a free workspace does not provide that capability.

The proposed low-traffic budget is **$93–97/month before tax/overages**, one Vercel
developer and Render Pro workspace, API 2 GB, PG 1 GB/10 GB disk, Clerk included
usage and a small AWS allowance. Exact regional pricing and billing eligibility
must be confirmed before approval. No free trials or credits are counted.

No commit, push, PR publication, deployment, resource creation or paid cloud action
was performed. Existing local data, images, accounts and shared test services were
preserved. Temporary health containers were removed. Only a new disposable
`pix_share_phase11_test` PostgreSQL database and scoped test media were used for
this phase's regression checks; no old dataset was copied into a staging target.

## Repository audit and checkpoint

Reviewed the tracked diff from HEAD and the untracked Phase 9/10 implementation:
storage adapter/router/reconciliation, configuration/auth/request boundaries,
serialization, DB/runtime settings, frontend headers/proxy/browser helpers,
dependencies/locks, Compose/Docker/CI and operational docs. Reviewed new Phase 11
changes separately. Existing UI components and migrations were not rewritten.
The default CI remains a local/test-database workflow, not a deployed staging
release pipeline; hosted smoke and image security gates still need explicit CI
integration after their deployment prerequisites are approved.

No accidental authentication bypass, destructive migration, early old-media
deletion or refresh-after-commit cleanup regression was found in the audited
paths. Backend row locking and ownership checks are preserved. Tests cover failed
commit cleanup, ambiguous uploads, partial deletion, metadata fallback and legacy
local references. A code review and scanner are bounded evidence, not proof of
the absence of all defects.

Private env files, `.aws`, original uploads, DB dumps/backups, caches/build output,
logs and browser states are excluded from Git and Docker contexts. Added
`staging-artifacts/` exclusions at root and in the frontend Docker context so
future session states/reports cannot enter container build contexts. Checked
representative real env paths and future smoke-state paths with `git check-ignore`.
No nondefault private environment value was found in the candidate source files
in an exact-value scan. Two local default PostgreSQL URL fields matched existing
examples/CI docs; inspected and classified as intentional loopback test defaults,
not privileged credentials. This does not replace a dedicated organization-wide
secret scanner or certify all historical Git objects.

The worktree contains accumulated changes; there is no new release commit.
Proposed storage/security/staging checkpoints and mixed-file split caveats are
in `RELEASE_CHECKLIST.md`. One coherent checkpoint is preferable to broken
intermediate commits if a hunk split cannot be validated. Do not automatically
stage all files or include raw scans, browser states or test fixtures. The Phase 8
HEAD cannot safely serve as an S3 rollback release.

## Changes made in this phase

- Digest-pin Python, uv and both Node Docker bases. Upgrade uv 0.11.21 to 0.13.5
  to remove the bundled vulnerable QUIC dependency identified by the image scan.
- Move the Node 24 runtime/build base from Debian bookworm to pinned trixie and
  remove unused npm/corepack from the standalone runtime only. Builders retain
  the locked pnpm toolchain; local workflows and API runtime entrypoint remain.
- Add `scripts/render_start.py`: explicit asyncpg scheme conversion, encrypted
  TLS requirement, conflict/insecure setting rejection, encoded-password
  preservation, Render `PORT`, original bounded Uvicorn options, generic startup
  errors without connection-string logging. Add 11 focused backend cases.
- Add `web/scripts/staging-smoke.mjs`: separate HTTPS/origin-bound real-browser
  staging workflow with two interactive signup/signin/logout bootstraps, UI
  upload/edit/replace/delete, responsive public browsing, actual nonowner 403s,
  variant MIME/render checks, SHA-256 checkpoint and persistence rechecks.
  No Clerk testing helper, development OTP shortcut or authentication mock.
- Add `scripts/check_staging_cleanup.py`: read-only checks of the two exact smoke
  object groups, separately verifying replacement and deletion independent of
  CDN cache. It performs no writes or broad bucket inventory.
- Add reviewed-example Render, runtime IAM, bucket/OAC and OIDC trust templates
  under `deploy/staging/`; placeholders only, no auto-discovered deploy manifest.
- Add the deployment plan and release checklist, and link them from README.

These scripts/templates are release preparation. The live provider paths and
new staging harness's complete hosted behavior are **unverified**, not newly
passing production workflows. Guard tests and syntax/lint are useful but do not
substitute for real infrastructure execution.

## Container builds and security results

Both original Dockerfiles built successfully. Trivy **0.76.1** was pulled and
used to scan the actual local images, including OS and embedded language tools.
Scanner image digest:
`sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c`.
The vulnerability DB was downloaded for this audit, then held fixed for the
before/after comparison. Counts are package/advisory occurrences, not unique
exploits. No ignore file or severity suppression was added.

| Image | Critical | High | Medium | Low | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| API initial | 0 | 46 | 67 | 62 | 1 |
| API updated candidate | 0 | 44 | 65 | 62 | 1 |
| Web initial | 1 | 60 | 95 | 84 | 2 |
| Web updated candidate | 0 | 43 | 58 | 60 | 1 |

Initial frontend findings included npm-bundled brace-expansion, http-cache-semantics
and undici; those tools are unnecessary in the standalone server and removed from
the runtime. Initial API uv/uvx each included `GHSA-4w2j-m93h-cj5j` in quinn-proto;
the updated uv scan has no High/Critical findings. The remaining High findings
are Debian OS packages, with **no fixed versions reported by this scanner DB**.
Both updated images have eight unique High advisory IDs:
`CVE-2025-69720`, `CVE-2026-16742`, `CVE-2026-54369`, `CVE-2026-76642`,
`CVE-2026-78408`, `CVE-2026-78409`, `CVE-2026-78410`, `CVE-2026-9538`.
Occurrence counts differ by installed packages. No blanket claim of
non-exploitability is made; map vulnerable code to installed runtime behavior,
vendor guidance, nonroot restrictions and exposure before accepting each risk.
[QUIC advisory](https://github.com/quinn-rs/quinn/security/advisories/GHSA-4w2j-m93h-cj5j).

The initial bookworm Critical `CVE-2023-45853` concerns MiniZip. Debian explicitly
notes its vulnerable contrib code is not built into the affected bookworm zlib
binary packages. The raw scanner finding is retained rather than silently
discarded; the updated trixie image no longer reports it.
[Debian vendor assessment](https://security-tracker.debian.org/tracker/CVE-2023-45853).

**Scanning execution: PASS. High/Critical policy gate: FAIL.** JSON output commands
return zero when a scan completes; that is not a vulnerability-free result.
Before any release, rescan the exact published registry digest with current DB,
archive its SBOM/raw report, triage each exception with owner/deadline or remediate
it, and obtain explicit risk acceptance. A local image ID is not a published
registry manifest digest. Vercel's hosted runtime is managed by Vercel; the local
web Docker OS scan does not certify that separate runtime.

### Repeatability and immutable releases

Executed **two independent `docker build --no-cache` builds per Dockerfile** using
the same pinned inputs. All four builds passed. Output IDs differ:

| Clean build | Local image ID |
| --- | --- |
| API A | `sha256:c9204de1b4a86aa7666f0621509f808eca3b16fc46f91f1b8a0bcf3c174aa327` |
| API B | `sha256:994298061dbfb9b39a02f1af12a216c54584d34f6954b4d8490934dd26950fe1` |
| Web A | `sha256:d732d65de1c2887c412fc32f9e0e1d07c04be7153859f13e62dfc09c657914cd` |
| Web B | `sha256:87023880960d6625ced0e503802d0aa945df3b03afd035345033b0a8a7102779` |

**Functional build repeatability: PASS. Byte-for-byte reproducibility: NOT
ESTABLISHED (image IDs differ).** API build timestamps differ; frontend Next build
IDs also differ. This comparison is not a complete binary-diff root cause analysis.
Do not rebuild to roll back. Build once, scan, publish by immutable digest and
retain the artifact; Vercel rollback selects the previous immutable deployment.
If bitwise reproducibility is a hard policy, keep that gate open: normalize
`SOURCE_DATE_EPOCH` and investigate generated build/crypto metadata without deriving
secret encryption keys from public commit hashes.
[Docker reproducible-build guidance](https://docs.docker.com/build/ci/github-actions/reproducible-builds/).

Local standalone builds used production compilation with development/empty
public Clerk configuration, **not a validated production Clerk deployment**.
No live keys were supplied as Docker build arguments. Production policy guards
remain intact; valid staging public build inputs must be supplied after approval.

## Health/readiness and local verification

Fresh PostgreSQL schema migrated to head without copying application rows.
Started the rebuilt API and web in temporary nonroot, read-only containers with
writable bounded tmpfs and local-only listeners. API used the disposable DB and
development configuration for health checks, not a claimed real auth session.
Observed `/health` **200**, `/ready` **200**, untrusted Host **400**, standalone
frontend favicon **200**. Containers ran as `appuser`/`node` with read-only rootfs;
both were removed afterward. This verifies local startup/DB readiness and static
web health, not Render probe behavior, TLS, Clerk login or an object outage.

| Check | This phase's result |
| --- | --- |
| Full backend regression | **PASS — 140 passed, 0 failed, 0 skipped**, 20.12s; includes 14 actual local MinIO cases and 11 new adapter cases |
| Fresh disposable DB migration | **PASS**, Alembic upgrade head |
| Ruff | **PASS**, no findings; NixOS uses the available glibc loader for the installed binary |
| basedpyright | **PASS**, 0 errors / 0 warnings |
| Frontend ESLint | **PASS** |
| Frontend TypeScript | **PASS** |
| Next production compilation | **PASS**, both clean Docker frontend builds include `pnpm build` and TypeScript |
| Staging runner guard tests | **PASS — 2 tests**, HTTPS/credential/path rejection and exact staging media namespace |
| Runner help/syntax | **PASS**, no cloud access or account changes |
| API/web Docker builds | **PASS**, initial + updated candidates + 2 independent clean builds each |
| Runtime image scans | **PASS execution / FAIL security gate**, counts above |
| Local container health checks | **PASS**, four HTTP assertions plus two nonroot/read-only checks |
| Git diff whitespace/privacy checks | **PASS** within the stated source/env-value scope |
| Hosted staging smoke / production Clerk | **NOT RUN**, no approved infrastructure or staging keys/accounts |
| Cloud OIDC/IAM/CloudFront/private S3 reads | **NOT RUN**, templates only; MinIO coverage does not verify AWS policies |
| Render restart/PITR / immutable cloud rollback | **NOT RUN**, approval and two compatible retained artifacts required |
| New Chromium/Firefox/WebKit product regression | **NOT RUN in Phase 11**, no product UI/auth changes; Phase 10 recorded 24 Chromium and 23 Firefox/WebKit tests with no skips, historical evidence only |

Initial unprivileged pnpm attempts could not access the existing cache database;
rerunning with permitted local cache access succeeded. The direct Ruff launcher
also needed the NixOS loader; that environment error was corrected for the actual
lint run. These are not application test failures. Commands/results and scans are
retained privately under `/tmp/pixshare-phase11`; temporary files are not durable
release artifacts and are not intended for Git or publication.

## Outstanding release gates and next action

See `RELEASE_CHECKLIST.md` for owners' approval/evidence gates and
`STAGING_DEPLOYMENT_PLAN.md` for practical commands, names-only credentials list,
manual provider configuration, smoke procedure, cost limitations and rollback.

Before deployment: resolve/accept remaining OS-image risks; approve artifact
promotion policy and budget/regions; prepare separate Clerk production instance
and stable HTTPS domains; verify private DB TLS tradeoff, exact origins/proxy
trust, S3 OAC/OIDC permissions and temporary-role refresh; establish backup and
two S3-compatible rollback artifacts; execute hosted smoke and measure resource
usage/recovery. CDN one-year caching means deletion does not immediately revoke
previous public image reads. Full CSP, ingress abuse protection and capacity are
still deployment-specific gates, not proven by local tests.

The infrastructure approval boundary has been reached with an actionable plan.
No cloud resources or existing user accounts need to be changed to review it.
