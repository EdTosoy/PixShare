# PixShare portfolio release

Recorded 2026-10-24. Repository: [EdTosoy/PixShare](https://github.com/EdTosoy/PixShare).
This release packages the accumulated implementation and finishes the interface
as a **simple online photo album**, without adding social-network features or
claiming a deployed live service.

## Final design decision

The user explicitly selected **Hallmark 2.0 Atelier**, then requested removal of
forest green and a simpler album identity. The implementation uses Atelier's
Sentient 300/400 display, Hanken Grotesk 400 reading face, warm paper, dark umber
ink, muted slate accent, outlined controls and thin print mats. Light and dark
modes share the same layout. There is no forest-green accent.

The 49-theme catalog and the actual Studio, Editorial, Darkroom, Atelier and
Specimen references were inspected. Atelier's typography/palette comes from its
installed theme/scaffold, translated into the existing token names and sRGB
convention. The theme dresses the existing application rather than adding a
marketing template. Decorative haze, noise, heavy shadows and motion were omitted
for this album. Photographs retain their color and full composition.

[Design specification](../design.md) · [Font provenance and notices](../web/public/fonts/atelier/README.md)

Sentient is loaded through Fontshare's official API. Its supplied license
restricts repository redistribution, so the downloaded Sentient binaries are
not included in this public repository. Hanken's unmodified WOFF2 assets and OFL
notice are included. Font failures retain readable fallback text; no build-time
font download is required.

## What changed

- The landing screen opens with “Your photographs, together” and the actual
  album, instead of decorative introductory labels and a large marketing gap.
- Navigation uses the existing destinations, a compact wordmark, a real SVG theme
  control, and “My album.” No route or authentication handler was removed.
- Landing, Explore and the personal album share dimension-aware cards, contain
  fit, source-ordered responsive rows, bounded captions and responsive variants.
  Sparse last rows stay bounded instead of stretching a single image.
- Upload/edit place the working picker next to the caption on desktop and stack
  them on mobile. Privacy text, validation, pending states and error focus remain.
- Detail, confirmation, loading, empty, success, error and retry surfaces share
  the same type, spacing, focus and color system. Native dialog behavior remains.
- Newly seeded demo copies are bounded and encoded to their declared formats.
  This repairs historical oversized/mislabeled fixture inputs without rewriting
  repository originals or existing media. The regression verifies preservation
  and idempotence against PostgreSQL.

The source-facing change is presentation plus the focused seed repair. Existing
Clerk sessions, query/API contracts, secure upload validation, ownership checks,
row locks and committed-media cleanup rules are preserved.

## Scope of the repository review

All accumulated changes were reviewed by file and responsibility: S3/media
routing and serialization; configuration/auth/request guards; database timeouts
and readiness; local/deployment packaging; pinned dependency/lockfile updates;
reconciliation and staging utilities; regression tests; UI; and documentation.
They belong to PixShare and are included in the release, rather than left as an
unexplained dirty tree. No application database/model/migration rewrite occurred.

Private working environments, accounts, runtime uploads, auth state, traces,
agent scratch records, backups and audit ownership bookkeeping are excluded.
Example environments contain only empty or explicit example values. The text
privacy scan compares candidate files against actual configured credential
values without printing or retaining the values. Screenshot accounts are masked;
public portfolio screenshots use fresh signed-out contexts and demo data.

The separate portfolio checkout has unrelated existing work. Its PixShare data
entry/case study and selected evidence are prepared separately; they are not
included in PixShare Git commits or published automatically.

## Verification

Executed on isolated local PostgreSQL databases:
`pix_share_release_test` for destructive pytest fixtures and
`pix_share_release_e2e` for browser data, both on a dedicated local instance.
Media uses a separate temporary directory. The optional S3 tests use a real,
loopback-only MinIO service and test-scoped object prefixes, not AWS resources.

| Check | Result |
| --- | --- |
| Backend full regression | **PASS — 141 passed**, including 14 real local MinIO cases and the new seed-preservation regression |
| Ruff | **PASS**, all checks |
| basedpyright | **PASS**, 0 errors/warnings/notes |
| Frontend ESLint | **PASS**, full frontend scope |
| TypeScript | **PASS**, `tsc --noEmit` |
| Next.js production build | **PASS**, Next.js 16.4.1; actual standalone server used for capture |
| Browser regression | **PASS — 30 passed, zero skipped, 2.7 minutes**, final Atelier build; setup, 24 public/device checks and five genuine Clerk journeys |
| Accessibility | **PASS**, all 53 final state captures: zero reported axe violations, zero incomplete rules and zero horizontal overflow; keyboard/dialog/reduced-motion/contrast checks also pass |
| Hallmark static sweep | **PASS — 0 Floor failures, 0 Reflex findings, 0 open warnings** over 25 app/component files |
| Hallmark kept record | **10/10 links and 24/24 handlers preserved** |
| Hallmark render tier | **NOT RUN**, Puppeteer absent; repository Playwright produced actual screenshots instead |
| Whitespace, local links and privacy | Rechecked against the final publication candidate |
| Hosted live demo / cloud policies / capacity | **NOT RUN**, no deployment or infrastructure provisioning |

[Final revision record](release/verification.json) ·
[Before/after screenshot index](release/SCREENSHOTS.md) ·
[Backend CI](https://github.com/EdTosoy/PixShare/actions/workflows/ci.yaml) ·
[Web CI](https://github.com/EdTosoy/PixShare/actions/workflows/web-ci.yaml)

The initial pre-Atelier design also passed all 30 genuine browser cases; its
results are not substituted for the selected theme's final run. Backend checks
are reused because the subsequent theme change touches no backend behavior.
Authenticated browser artifacts remain private; screenshots mask the account
control and save no storage state or tokens.

Hallmark's remaining color-pair warnings were dismissed after checking actual
rendered pairings: `accent-ink` belongs on the accent fill, not the paper. Its
container-width finish note is answered: album, forms and detail have different
reading tasks on separate routes. Numeric state headings are prose rather than
numeric comparisons. The finish review was conducted in-thread as the installed
Codex harness specifies; the leftover dialog eyebrow was removed and recaptured.
No automated accessibility-conformance certification is claimed.

## Image optimization evidence

The final browser-selected representations for three freshly normalized demo
photos total **91,058 response-body bytes**, versus **3,333,388 bytes** for their
stored originals: **97.27% smaller** at desktop, tablet and mobile, DPR 1.
See [raw measurements](release/image-performance.json).

This measures the actual source selected by the browser and actual HTTP response
bodies for this fixture set. It excludes fonts/scripts/headers and is not a
production LCP, latency, load or general compression guarantee. The seed copies
are newly normalized photos; the historical Phase 8 comparison uses different
original media and remains labeled separately. API user uploads still preserve
original bytes. Variant failure still falls back to originals.

## CI repair and publication

Before this release, GitHub's backend CI passed but Web CI failed before
application tests with Chromium's “No usable sandbox” error. The updated job
keeps `chromiumSandbox: true`, selects the installed full Chromium binary and,
only when required, installs a runner-local AppArmor profile for that exact
binary's user namespace. It does not disable the browser sandbox or change a
workstation policy. This follows
[Chromium's documented per-executable approach](https://chromium.googlesource.com/chromium/src/+/main/docs/security/apparmor-userns-restrictions.md).
The test API also gets an explicit audit-only read budget. Production defaults
are unchanged. Public CI requires no Clerk secrets; authenticated local evidence
is stated separately.

The authorized publication uses ordinary commits and a fast-forward push to the
existing unprotected `main` branch. The remote tip/protection state is checked;
no force push, merge or cloud deployment is authorized by these operations.
The final response records the actual published SHA and CI run URLs after they
are confirmed, rather than inventing a success in advance.

## Known limitations

Public media is not a private vault. Originals retain metadata; there is no
moderation, private-sharing or account-deletion product workflow. PostgreSQL and
storage cannot commit atomically; orphan reconciliation stays operator-invoked.
Read throttles are per process, offset pages can drift, and cached public media
can outlive deletion. Actual AWS IAM/OIDC/CDN policy, disaster recovery, production
load and physical-device/screen-reader combinations need their own verification.
Sentient's browser availability depends on Fontshare, with a readable fallback.
Docker OS-image risks and hosting prerequisites in the earlier release checklist
are not erased by a visual redesign. No public live demo is claimed.

## Reproduction and reversal

Follow the README's isolated database instructions. Relevant entrypoints are
`uv run pytest -q`, `uv run ruff check .`, `uv run basedpyright`, and in `web/`:
`pnpm lint`, `pnpm typecheck`, `pnpm build`, `E2E_REQUIRE_AUTH=1 pnpm test:e2e`.
On this NixOS workstation installed executables were used directly where the
pnpm cache/native-loader launcher was unavailable; exact commands are in the
revision record. No lockfile was regenerated to work around the host.

Full workflow captures use `web/scripts/ux-audit.mjs` with
`UX_AUDIT_ISOLATED=1 UX_AUDIT_OUTPUT=../docs/release/screenshots` and
`before`, `after`, or `cleanup`, against separate E2E data and real development
Clerk accounts. Only that audit's recorded upload is cleaned. Delays/aborts
produce loading/error states; successful responses remain real.

The visual implementation is localized to styles, route composition and existing
components. Revert its specific commit to restore the previous UI while keeping
backend/storage work. Reverse the separate backend commit only as a whole after
reviewing the runtime/config/lockfile relationships. No data migration or cloud
rollback is part of this release.
