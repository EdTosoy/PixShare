# PixShare web

Next.js 16.3 App Router, React 19, Clerk 7, TanStack Query 5, Tailwind 4.
Use Node 24+ and the pinned pnpm version.

```bash
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

Set matching Clerk keys and `NEXT_PUBLIC_API_URL` in `.env.local`.
Public pages work without Clerk configuration. Mutations require real Clerk
sessions verified by FastAPI. The backend and PostgreSQL must run separately.

```bash
pnpm lint
pnpm typecheck
pnpm build
pnpm start
pnpm test:e2e
```

See the [root README](../README.md) for environment setup, isolated test database
commands, Clerk browser-test prerequisites, and production limitations.
