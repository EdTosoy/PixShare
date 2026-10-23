<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# PixShare frontend conventions

Use pnpm and preserve the lockfile. Route files compose reusable components;
API access belongs in lib/. Read the installed Next.js 16.3 documentation for
page params, proxy, images, and testing before changing those integrations.
Keep Clerk as the real authentication source; AuthGate is UI, not authorization.
Private query keys include identity and the query provider resets on account
changes. Invalidate post queries after writes.

Use the CSS tokens for both themes. Preserve keyboard focus, native dialog focus
management, reduced-motion behavior, narrow layouts and readable error states.
Keep JPEG/PNG/WebP and 10 MiB validation consistent with FastAPI. Browser tests
use real local API/PostgreSQL data. The Clerk journey requires explicitly
configured development-instance keys and two dedicated accounts; skip it with
an explanation if these are absent. Never fake sign-in in production code.
