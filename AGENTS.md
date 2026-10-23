# PixShare working agreements

Read README.md, docs/ARCHITECTURE.md, and applicable web/AGENTS.md before editing.
Use implement-feature for features, fix-bug for defects, and verify-changes before
reporting implementation complete. Inspect installed framework docs when APIs
are version-sensitive. Keep changes focused and preserve existing user work.

- Preserve FastAPI, PostgreSQL, SQLAlchemy, Alembic history, Clerk and the pnpm/uv
  lockfiles. Do not rewrite the application or substitute mocked product data.
- Public reads stay public. Authenticate API mutations and verify ownership in
  the backend. Never add an authentication bypass to make a test pass.
- Validate upload content and size. Commit before deleting old media. Clean new
  uploads only on commit failure, never after a committed write's refresh fails.
  Preserve row locking for concurrent replacements/deletion.
- Treat media URLs as public locations, not authorization. Keep storage behind
  its interface; local development must not require cloud resources.
- Keep secrets, JWTs, SQL parameters and private environment values out of logs,
  diffs, screenshots and documentation. Example environment files contain no keys.
- Run pytest only on a disposable PostgreSQL database ending in `_test`: fixtures
  delete its rows. Browser tests use separate test data and dedicated Clerk users.
- Relevant checks: `uv run pytest -q`, `uv run ruff check .`,
  `uv run basedpyright`; in web: `pnpm lint`, `pnpm typecheck`, `pnpm build`,
  `pnpm test:e2e`. Record prerequisites, skipped checks and failures honestly.
- Commits, pushes, PRs, merges, deployments and paid resources require explicit
  authorization. Local reversible implementation and verification may proceed.
