# Phase 6 — authentication and real-user verification

Phase 7 follow-up: the seven Ruff findings recorded below have been addressed.
See [the UI/UX audit](UX_AUDIT.md) for current lint and regression results; the
Phase 6 results below remain a historical record.

Recorded 2026-10-23; updated after the user supplied development keys and created
both test accounts. **The full strict browser suite passes: 16 passed, zero skipped.**
Both configured users exist, their emails are verified, and their Clerk IDs are
distinct. Matching development keys were validated with HTTP 200 from Clerk's
backend and frontend JWKS endpoints; their public signing keys match. Key values,
account addresses, JWTs and passwords are omitted from this report.

## Latest real-account verification

| Check | Result |
| --- | --- |
| Clerk-enabled production build | PASS: Next 16.3.0, including `/sign-up` |
| Backend `uv run --no-sync pytest -q` | PASS: 65 passed in 7.83s |
| basedpyright 1.39.9 | PASS: 0 errors/warnings/notes |
| Frontend ESLint and TypeScript | PASS |
| Real form login/logout, signed-out browsing and account switching | PASS |
| Real registration, email verification, required organization onboarding, logout/login | PASS |
| Authenticated upload, edit/clear caption, genuine PNG replacement and owner deletion | PASS |
| Distinct identities, private-gallery separation, hidden owner controls, non-owner PATCH/DELETE 403 and unchanged post | PASS |
| Public access to a real user's image; deleted post returns 404 | PASS |
| Full strict browser suite | PASS: 16 passed, zero skipped, 1.6m |
| Locked Ruff 0.16.1 | FAIL: the same 7 existing findings listed in the initial record below |

Final browser command (from `web/`):

```bash
E2E_REQUIRE_AUTH=1 NEXT_TELEMETRY_DISABLED=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/etc/profiles/per-user/edtosoy/bin/chromium node node_modules/@playwright/test/cli.js test
```

The local runner still uses installed executables directly because the pinned
pnpm download/signature check was unavailable, as described in the initial
record. No dependency install, lockfile change or signature-check override was
needed. Authentication acceptance is verified; overall lint remains failed on
the seven existing Ruff findings. An independent human acceptance session and
the additional authentication methods listed below remain unverified.

The latest run uses fresh disposable `pix_share_phase6_real_test` and
`pix_share_phase6_real_e2e` databases on local PostgreSQL port 55439. Backend media
is `/tmp/pixshare-phase6-real-backend-uploads`; browser media is
`/tmp/pixshare-phase6-real-uploads`. The API verifies genuine Clerk sessions and
fetches the instance's JWKS. No backend authentication dependency is replaced
in browser tests. Official Clerk testing tokens support automated development
flows; application signature, origin, ownership and upload checks remain intact.

Live verification exposed and repaired these additional issues:

- The local launcher bound to `127.0.0.1` while the browser origin was `localhost`.
  Clerk's same-origin middleware rewrite was treated as an external request,
  causing socket resets and a web-server startup timeout. Binding the local
  launcher to `localhost` reproduced the fix. `PIXSHARE_HOST` remains overridable.
- Standalone startup changes the working directory and could not find the
  frontend's local environment file. A normal startup probe returned HTTP 500.
  The launcher now uses Next's bundled `@next/env` loader before starting the
  standalone server; the identical probe then returned HTTP 200. Secrets stay
  outside the standalone output. No new dependency was added.
- With this instance's required username/password and organization onboarding,
  the combined SignIn registration flow reached an empty form. PixShare now has
  an explicit public `/sign-up` route with Clerk's SignUp component, linked from
  SignIn through the provider. Registration and pending session tasks stay in
  Clerk's actual UI. See [Clerk's separate-page guide](https://clerk.com/docs/nextjs/guides/development/custom-sign-up-page).
- Tests now choose the enabled email-code alternative when the form initially
  asks for a password, and wait for code preparation before entering the test
  OTP. Registration fills enabled username/name/password fields and completes
  the instance's required organization task. It creates one uniquely named test
  organization when required and deletes only that exact organization associated
  with its generated test user. Existing settings and users are preserved. See
  [Clerk's session-task requirements](https://clerk.com/docs/guides/development/custom-flows/authentication/session-tasks).
- The demo PNG/WebP files are actually JPEG bytes. The API correctly rejected
  the demo PNG replacement with HTTP 400. The browser replacement test now
  supplies a small genuine PNG and retains the validation/ownership assertions.
  Existing demo files and application media were not rewritten. Their misleading
  extensions remain a demo-data limitation.
- Test selectors now target the upload error rather than colliding with Next's
  route announcer, and assert the actual `?success=updated` redirect contract.

Authenticated screenshots, video and traces remain disabled. Temporary signup
passwords are generated in memory; password-entry failures are sanitized.
Generated signup users and organizations are cleaned up in `finally`; the two
persistent user-supplied test accounts are preserved. This is real-browser
automation, not an independent human acceptance session. Social login, MFA,
password-reset flows and real email delivery remain unverified.

Final cleanup audit: both persistent test accounts remain; zero generated signup
users and zero generated signup organizations remain. The configured secret key
has zero occurrences in the browser's static assets. The temporary API and
PostgreSQL processes were stopped; disposable database/media files were retained.
No commits, pushes, deployments, production changes or paid resources were used.

## Initial configuration audit (before the user completed setup)

| Location / setting | Observed state | Requirement |
| --- | --- | --- |
| Root `.env`: `CLERK_SECRET_KEY` | Empty | Matching Clerk development secret, `sk_test_…`, for API JWKS verification |
| Root `.env`: `CLERK_JWT_KEY` | Empty | Optional public PEM alternative; unnecessary with the secret/JWKS path |
| Root `.env`: publishable keys | Empty | Frontend needs `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_…` |
| `web/.env.local` | Absent | Frontend publishable key and server-only `CLERK_SECRET_KEY` for Next's Clerk integration |
| Process/test files: `E2E_USER_EMAIL`, `E2E_OTHER_USER_EMAIL` | Absent | Two distinct, existing dedicated Clerk development users |
| Root `.env`: authorized parties | Configured | Must include the actual browser origin, normally `http://localhost:3000` |
| Testing token | Absent | Generated by `clerkSetup()`; do not manually document or persist it |

Only presence and key type were inspected; key values were never printed.
Account existence and instance settings cannot be checked without credentials.
No configured E2E accounts or frontend environment file were available. Seeded
`demo_user_1` is a database identity, not a Clerk account.

`app/api/routes/auth.py` verifies session tokens through the actual Clerk SDK,
including configured authorized parties. `get_current_user` provisions a local
user from the verified subject. `app/api/routes/posts.py` enforces ownership and
row locking for PATCH/DELETE. Public GET routes require no identity. Backend
verification does not read `CLERK_PUBLISHABLE_KEY`; that retained setting is also
accepted as an alias by the browser test setup. No custom JWT template is needed:
the frontend calls Clerk's default `getToken()`.

`web/app/providers.tsx` mounts Clerk when a publishable key is configured and
resets the query cache on identity changes. `web/proxy.ts` installs Clerk's
middleware without making public pages private. `/sign-in` uses the real Clerk
`SignIn` component. Initially this used the combined account-creation flow;
the live repair above introduces the separate `/sign-up` route. See
[Clerk's combined form guide](https://clerk.com/docs/nextjs/guides/development/custom-sign-in-or-up-page).

## Issues found and changes

- Playwright checked environment variables before Clerk's own dotenv loading.
  Local frontend keys could therefore be present while the suite skipped them.
  It also demanded `CLERK_PUBLISHABLE_KEY` while the frontend uses
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`. The runner now loads ignored local files
  before evaluating prerequisites and uses either name, rejecting mismatches.
- Setup and journey had different prerequisite checks. They now share one list;
  setup verifies that the two emails resolve to distinct existing Clerk IDs.
  Production keys and non-test email addresses are rejected. Explicit
  `E2E_REQUIRE_AUTH=1` stops immediately on missing configuration.
- The original helper-based CRUD test did not test authentication forms,
  registration, logout, DELETE ownership denial, or distinct account IDs.
  Separate form journeys now cover login/logout/account switching and new-user
  registration followed by login. CRUD coverage also checks caption clearing,
  private gallery separation, public access to the new image, hidden owner
  controls, both API denials, unchanged data after denial, and deletion/404.
- Cleanup captures the created post ID from the API response before asserting
  redirect success. Only that post is deleted. Registration creates a random
  `pixshare-phase6-…+clerk_test@example.com` user and cleans up only that exact
  generated identity; the two persistent accounts are preserved. An interrupted
  run may require manually removing its generated user/post in the test system.
- Auth/setup projects disable screenshots, video, and traces, which can contain
  session headers, cookies and testing tokens. Errors from credential-bearing
  setup requests are sanitized. Do not enable verbose Clerk or HTTP debugging
  when sharing test results. Public browser artifacts remain ignored.
- Ten backend tests failed when `UPLOADS_DIR` pointed outside the workspace:
  they inspected hard-coded `uploads/` paths; two media tests also wrote there.
  Four test modules now use the API's configured upload directory, preserving
  all assertions and allowing media isolation. The rerun passed all 65 tests.

At this initial stage, live defects could not be reproduced without credentials.
The subsequent live findings and repaired hosted workflows are recorded above.

## Exact manual setup

1. In the [Clerk Dashboard](https://dashboard.clerk.com), select a **development**
   instance dedicated to testing. Enable email sign-in/sign-up and email codes.
   The suite chooses the available email-code alternative for existing users;
   registration supplies required username/password and enabled name fields.
   Required organization onboarding is completed through Clerk's UI with a
   generated test organization. Phone, social-login and MFA journeys remain
   outside this suite's current coverage. Use a suitable
   dedicated development instance; do not weaken an existing application's
   security settings to make tests pass. Keep Clerk's development test mode
   enabled. Permit new sign-ups for the registration journey.
2. Copy `web/.env.example` to `web/.env.local` if it does not already exist.
   Preserve existing files. Copy the development publishable and secret keys
   from that **same** instance into the following ignored files using an editor:

   | File | Variables |
   | --- | --- |
   | `.env` | `CLERK_SECRET_KEY`; `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` for Compose; optionally matching `CLERK_PUBLISHABLE_KEY` |
   | `web/.env.local` | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`; server-only `CLERK_SECRET_KEY`; `NEXT_PUBLIC_API_URL=http://localhost:8000` |

   Keep `CLERK_JWT_KEY` blank for JWKS verification. Set backend
   `CLERK_AUTHORIZED_PARTIES=http://localhost:3000` and
   `CORS_ORIGINS=http://localhost:3000`. Keep the sign-in URL `/sign-in` and both
   fallback redirects `/me`. Use `localhost` consistently in the browser.
   Never put a secret key in `NEXT_PUBLIC_*`, command history, or documentation.
3. Create two dedicated users in this development instance, using two separate
   addresses such as `owner+clerk_test@example.com` and
   `other+clerk_test@example.com`. These are examples, not configured accounts.
   You can create them via the dashboard or the app's `/sign-up` page.
   Put their addresses in the ignored `web/.env.e2e.local` file:

   ```dotenv
   E2E_USER_EMAIL=owner+clerk_test@example.com
   E2E_OTHER_USER_EMAIL=other+clerk_test@example.com
   ```

   The two emails must identify different Clerk users, not aliases of one user.
   Existing-account passwords are not stored by the suite; it uses the enabled
   email-code alternative. Registration generates a password in memory when the
   instance requires one. Clerk development
   test addresses use `424242` for email-code verification; they do not prove
   email delivery. See [official test email guidance](https://clerk.com/docs/guides/development/testing/test-emails-and-phones).
4. Prepare a **new disposable E2E database**, separate from both application data
   and pytest. The following assumes the README's local Compose PostgreSQL on
   port 5432. If the name already exists, choose a fresh name; do not drop it.
   From the repository root:

   ```bash
   docker compose up -d postgres
   docker compose exec postgres createdb -U postgres pix_share_phase6_e2e
   export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pix_share_phase6_e2e
   export UPLOADS_DIR="$(mktemp -d /tmp/pixshare-phase6-e2e.XXXXXX)"
   uv run alembic upgrade head
   uv run python -m scripts.seed_db
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   The seed command adds only bundled demo images to this new database. Leave
   this API running. Stop any other API/frontend on ports 8000/3000 first.
5. In another terminal, rebuild the frontend with the real publishable key and
   run strict auth verification, then the complete suite:

   ```bash
   cd web
   pnpm build
   pnpm exec playwright install chromium  # only if Chromium is not installed
   E2E_REQUIRE_AUTH=1 pnpm test:e2e --project=auth
   E2E_REQUIRE_AUTH=1 pnpm test:e2e
   ```

   Playwright starts the production frontend and refuses to silently reuse a
   server on port 3000. Only set `E2E_BASE_URL` when intentionally using an
   already-running isolated test frontend. An existing system Chromium can be
   selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`; its sandbox stays enabled.
   Shell environment values take precedence over `.env.e2e.local`, `.env.local`,
   then `.env` in `web/`. Keep test account addresses in `.env.e2e.local` and app
   keys in `.env.local` so the build and runner use the same keys.
6. For an independent human acceptance check, use `/sign-up` to create a new
   dedicated test user and complete required onboarding; log out; sign back in; upload an
   image; edit its caption and replace it; inspect it signed out; then inspect
   it as the second user in a separate browser profile. The second user must
   have no owner controls and must be denied editing. Return as the owner and
   delete only the test post. Record results without tokens, account screenshots,
   passwords or private environment values. Run the automated direct API denial
   assertions to verify the backend boundary as well as the UI.

The CRUD journey uses [official Clerk helpers](https://clerk.com/docs/guides/development/testing/playwright/test-helpers)
to obtain genuine sessions. Helper-based ticket sign-in does not itself prove
credential entry, so the form journeys are separate. Official testing tokens
support Clerk's automated test mode; the application's session signature,
origin and ownership checks still execute unchanged.

## Initial verification record (before credentials were available)

Native PostgreSQL 17.11 ran on isolated port 55439. New databases:
`pix_share_phase6_test` for pytest and `pix_share_phase6_e2e` for the browser.
Media directories were under `/tmp`, separate for the two suites. Existing
databases and migrations were preserved. The build used empty Clerk keys.

| Check | Result |
| --- | --- |
| Existing Alembic migrations on both new databases | PASS |
| Initial isolated-media pytest run | FAIL: 10 path-assumption failures, 55 passed; fixed as described above |
| `uv run --no-sync pytest -q` with isolated test DB/media | PASS: 65 passed in 7.89s |
| `ruff check .` using installed native Ruff 0.15.14 | PASS; this older version is not authoritative for the locked version |
| Locked Ruff 0.16.1 via Nix ELF loader | FAIL: 7 existing lint findings (listed below) |
| `node .venv/lib/python3.12/site-packages/basedpyright/index.js` | PASS: installed 1.39.9, 0 errors/warnings/notes |
| `node node_modules/eslint/bin/eslint.js .` in `web` | PASS; equivalent to `pnpm lint` |
| `node node_modules/typescript/bin/tsc --noEmit` in `web` | PASS; equivalent to `pnpm typecheck` |
| `node node_modules/next/dist/bin/next build` in `web` | PASS: Next 16.3.0 production build, TypeScript and all routes |
| `node node_modules/@playwright/test/cli.js test` in `web` | PASS for 12 public tests; 4 explicit skips (Clerk setup + 3 live journeys), 32.5s total |
| `E2E_REQUIRE_AUTH=1 … test --project=auth --list` | EXPECTED FAILURE: lists the four absent prerequisite variable names without values |
| `git diff --check` | PASS |
| Live Clerk forms, sessions/JWKS, authenticated CRUD and two-account browser checks | SKIPPED: no development credentials/accounts |
| Configured-Clerk frontend build/runtime, password/social/MFA flows, real email delivery | NOT RUN |

The exact local pytest environment overrides were `TEST_DATABASE_URL` pointing
to `pix_share_phase6_test` on port 55439 and
`UPLOADS_DIR=/tmp/pixshare-phase6-backend-uploads`, plus writable
`UV_CACHE_DIR=/tmp/pixshare-uv` and a Nix libstdc++ library path. The browser used
the API on port 8000, the built frontend on port 3000, and system Chromium with
its sandbox enabled. Backend RSA integration tests use ephemeral test signing
keys with the real Clerk SDK; they do not establish hosted Clerk behavior.

Package script attempts were blocked when pnpm could not fetch/verify the pinned
11.11.0 release. No signature check was disabled and no lockfile changed; the
already-installed script executables were run directly. The uv Ruff and
basedpyright entry points hit Nix executable-loader incompatibilities. Running
basedpyright's `index.js` through system Node resolved its launcher problem;
invoking `dist/pyright.js` directly was an incorrect entry point and produced
typeshed lookup errors. The locked Ruff binary did run with
`/nix/store/znb3q6g1ik34454j3vcjx824h1871asg-glibc-2.42-84/lib/ld-linux-x86-64.so.2 .venv/bin/ruff check .`.
It found four import-order findings (one each in `app/api/dependencies.py` and
`app/core/upload.py`, two in `tests/api/posts/test_create.py`), two UTC-alias
findings (`tests/api/posts/test_lifecycle.py` and `tests/test_auth_integration.py`),
and BLE001 for the broad exception handler in `app/api/routes/posts.py:42`.
These patterns existed before this task's edits. They were not silently changed
as part of authentication verification. In particular, narrowing or removing the
post-commit cleanup handler would change the media lifecycle: it intentionally
keeps a committed write successful and logs no exception details that could
contain private paths or parameters. Resolve that lint policy separately while
preserving those invariants; no lint rule was suppressed here. The first build
failed because the sandbox denied Turbopack worker sockets. Its failing cache was moved
aside under `/tmp`; the rebuild with local socket access passed. No repository
check, Chromium sandbox, or application security setting was weakened.

At that initial stage, Phase 6 remained incomplete. There were no commits,
pushes, deployments, paid resources, Clerk account creation, or changes to
application data in the initial run. The latest run above creates and cleans
only its own generated development signup user/organization and local test posts.
The temporary API and PostgreSQL test processes were stopped afterward; their
disposable databases and media files were preserved.
