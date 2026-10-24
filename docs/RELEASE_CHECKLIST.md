# PixShare release checkpoint and staging gates

Prepared 2026-10-24. **CONDITIONAL GO for the architecture; NO-GO for deployment
until the unchecked gates below are satisfied and infrastructure is approved.**
This checklist grants no authorization to commit, publish, deploy or spend.

## Local preparation

- [x] Review tracked changes and untracked Phase 9/10 implementation against HEAD
  `632b15c`; preserve all existing work, migrations, accounts and uploaded files.
- [x] Confirm runtime `.env` files, AWS config, uploads, backups, browser states,
  logs and build artifacts are excluded; extend exclusions for staging evidence.
- [x] Build local API and standalone frontend Docker candidates with locked
  dependencies and digest-pinned base images; independently rebuild each.
- [x] Scan actual runtime images; retain raw JSON locally and document findings.
- [ ] Resolve or explicitly approve the remaining High OS-package findings.
  A scanner exit of zero for JSON generation is not a security gate pass.
- [ ] Approve the build-once/promote-by-digest policy or complete deterministic
  byte-for-byte build work. Clean rebuilds currently produce different image IDs.
- [x] Prepare Render port/asyncpg adapter, guarded real-session smoke commands,
  least-privilege policy templates and provider configuration instructions.
- [x] Document current local checks separately from historical Phase 10 browser
  results. Hosted staging smoke remains NOT RUN.

## Proposed commit structure — only after separate authorization

The worktree contains accumulated Phase 9/10 work, not an already committed
release. Use three logical checkpoints; do not blindly stage every dirty file.

1. **Storage foundation:** S3 adapter/router/reconciliation, configuration/interface
   and serialization integration, isolated MinIO setup, storage tests, Phase 9
   architecture/API docs and AWS dependencies/lock entries.
2. **Release security:** JWT Bearer-only boundary, production config/origin guards,
   bounded request/readiness/DB controls, frontend headers, dependency security
   updates, real-browser helper fixes, CI and Phase 10 runbook/report.
3. **Staging preparation:** Phase 11 docs, Render launch adapter and tests, smoke
   runner/read-only cleanup checker, policy/Render templates, container base pins,
   uv security update, smaller frontend runtime and private evidence exclusions.

Several files mix checkpoints: `app/core/config.py`, `app/main.py`, environment
examples, dependency locks, Dockerfiles, Compose/CI, README and architecture docs.
Use reviewed hunks or prefer **one coherent release checkpoint** if splitting would
leave intermediate commits broken. Never regenerate a lockfile solely to split
history. Run the relevant checks after each actual staged candidate; current
worktree results do not certify an arbitrary hunk split. Do not include runtime
fixtures, raw scans/traces, local Git evidence or any real environment files.

## Infrastructure and billing approval

- [ ] Owner approves named providers, region, isolation, domains and charges;
  proposed budget $93–97/month before tax/overages, subject to live quote.
- [ ] Billing alerts/spend settings, administrative MFA, operators and retention set.
- [ ] Separate empty PostgreSQL, S3 bucket/prefix, Vercel/Render projects and Clerk
  application confirmed; no local users or datasets copied.
- [ ] Render Pro OIDC role exact service/environment subject verified; registry
  pull credential read-only and distinct. Static credential alternative needs
  explicit exception, rotation and revocation procedure.
- [ ] TLS decision approved: private Render DB `ssl=require` does not authenticate
  its self-signed certificate; external DB must use `ssl=verify-full`.
- [ ] Private S3 + all Public Access Blocks + owner-enforced ACLs + encryption +
  versioning/retention; CloudFront OAC scoped to images and exact distribution.
- [ ] Budget recalculated for selected AWS region/CDN plan and expected load;
  no unsupported free-tier assumption used.

## Deployable release gates

- [ ] Approve checkpoint commit/push/registry publication separately. Record full
  source SHA, lockfile hashes, platform, scanner version/DB date and source scope.
- [ ] Scan **published digest**; archive SBOM/scan and triage with owner, deadline
  and exploitability evidence for each accepted exception; no blanket ignore.
- [ ] API image registered by immutable registry manifest digest (local image ID
  is not a registry digest); Vercel immutable deployment ID/URL recorded.
- [ ] Required environment names reviewed in the staging plan; public build
  values match runtime, all private keys in provider secret stores only.
- [ ] Production Clerk instance DNS/TLS, allowed domains/redirects, matching live
  keys and actual email signup verified. Generic dev redirect warnings are not
  evidence that production is safe; capture only sanitized warning summaries.
- [ ] Exact HTTPS CORS/authorized parties/API allowed hosts (including Render
  health hostname); HTTP redirects, secure cookies and baseline CSP checked.
- [ ] Migration job succeeds once before traffic; current/head revision recorded.
  No destructive migration, seed restore, backfill or automated downgrade.
- [ ] `/ready` succeeds through Render health host and public HTTPS; DB outage
  produces 503 while liveness remains 200; object outage/recovery separately tested.
- [ ] Image memory/CPU under realistic concurrent maximum uploads measured;
  2 GB / concurrency 8 is a proposed initial bound, not verified capacity.
- [ ] Proxy trust/client rate-limit attribution verified; shared budgets and
  direct API exposure accepted for limited testers or ingress protection added.
- [ ] CDN deletion-cache retention disclosed and accepted; immediate revocation
  cannot be promised with immutable one-year caching.

## Hosted acceptance and recovery evidence

- [ ] `public` smoke: public HTTPS, 200 readiness/gallery, 401 private boundary,
  exact CORS and desktop/tablet/mobile layout.
- [ ] `bootstrap-owner` / `bootstrap-other`: new verified distinct staging users;
  actual sign-up, sign-out, protected signed-out view and real sign-in.
- [ ] `crud`: authenticated UI upload, optimized CDN variant rendering, caption
  editing, immutable replacement and real two-account 403 ownership checks.
- [ ] Read-only cleanup checker: replaced group absent at S3 origin.
- [ ] `persistence`: baseline exact post/metadata/hash captured; repeat after
  operator-approved API restart with provider event and recovery duration.
- [ ] Two S3-compatible immutable releases retained; rollback API digest and Vercel
  deployment, repeat persistence checks and record DB/config compatibility.
  Phase 8 HEAD is not a valid S3 rollback target.
- [ ] `cleanup`: UI deletion/post 404, both created groups absent at S3 origin;
  retained versions/caches distinguished from current object cleanup.
- [ ] Paid DB backup + versioned media restore rehearsed into approved isolated
  targets; RPO/RTO measured. Restores may create additional billable resources.
- [ ] Monitoring/log privacy/budget alerts have owners and verified notifications.
- [ ] Reports contain exact PASS/FAIL/BLOCKED results, timings and immutable
  provider IDs; browser states/tokens/private logs remain outside Git.

When all applicable gates pass and the owner grants deployment approval, staging
can become **GO**. Wider production exposure requires a separate assessment and
approval. This preparation ends before that boundary.
