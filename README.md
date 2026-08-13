# PixShare

PixShare is a full-stack media-sharing demo: a production-minded FastAPI backend that implements secure, async file uploads and media lifecycle patterns, paired with a minimal Next.js frontend. It demonstrates authenticated user ownership, multipart uploads, safe file validation and replacement, storage abstraction, and PostgreSQL persistence with migrations and tests.

## Highlights

- FastAPI async backend with REST endpoints for posts (upload/replace/delete)
- Server-side image validation and verification (JPEG / PNG / WebP, max 10 MB)
- Storage backend abstraction (local or remote object store)
- PostgreSQL persistence with Alembic migrations
- Minimal Next.js frontend in `web/` demonstrating upload and browsing
- Integration tests and CI-ready configuration

## Key features

- Authentication and per-user ownership checks for create/update/delete operations
- Multipart file uploads handled safely with content verification (Pillow)
- Safe image replacement: upload new object first, commit DB, then remove old object; roll back and cleanup on failure
- Static upload serving mounted at `/uploads` (see `app/main.py`)
- Pagination, filtering, and sorting for post listing endpoints

## Quickstart (recommended: Docker Compose)
The repository includes a Docker Compose configuration for local development and integration testing.

From the repository root:

```bash
# Build and start all services (API, DB, etc.)
docker compose up --build
```

- API will be reachable at http://localhost:8000 by default
- Frontend at http://localhost:3000

## Run the API locally (no Docker)

1. Create and activate a Python virtual environment and install dependencies (pyproject.toml / your package manager of choice).
2. Ensure a PostgreSQL database is available and set DATABASE_URL (or see app/core/config.py for exact variable names).
3. Apply migrations and run the server.

Example commands:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Environment variables

See `app/core/config.py` for the exact set of configuration variables. Typical values you'll need:

- DATABASE_URL — Postgres connection string (e.g. postgres://user:pass@localhost:5432/pixshare)
- STORAGE_BACKEND / S3_* variables — credentials and bucket if using S3-compatible storage
- SECRET_KEY / AUTH related variables — if the auth implementation requires them

## API (selected endpoints)

Base URL: http://localhost:8000

- GET /posts
  - Query params: limit, offset, file_type, sort (newest|oldest)
  - Returns: paginated list of posts

- GET /posts/{post_id}
  - Returns: single post (UUID)

- POST /posts
  - Authenticated. Form multipart: `file` (image), `caption` (optional)
  - Validates image type & size, uploads to configured storage, persists Post record

- PATCH /posts/{post_id}
  - Authenticated + owner-only. Accepts new `file` (optional) and `caption`
  - Uploads new file, updates DB, deletes old file after successful commit; if commit fails, the new file is removed

- DELETE /posts/{post_id}
  - Authenticated + owner-only. Deletes storage object and DB record

## Upload validation

Upload validation and verification are implemented in `app/core/upload.py` and enforce:

- Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`
- Max file size: 10 MB
- The server verifies the actual image format via Pillow (not just content-type)

## Frontend

The `web/` directory contains a Next.js app built with TypeScript. To run it locally:

```bash
cd web
npm install
npm run dev
```

The frontend demonstrates listing posts and an upload UI that consumes the API.

## Database & Migrations

Alembic is configured; migration scripts are in `migrations/` and the configuration is in `alembic.ini`.

Apply migrations before running against a fresh DB:

```bash
alembic upgrade head
```

## Tests

Integration tests are present under `tests/`. Run the suite with:

```bash
pytest
```

## Development notes

- The storage layer is abstracted under `app/storage/` so you can switch between local filesystem storage for development and an object store (S3/GCS) in production.
- Upload validation lives in `app/core/upload.py`. The posts routes and safe replacement logic are in `app/api/routes/posts.py`.
- Authentication routes are in `app/api/routes/auth.py`.

## Contributing

Contributions, issues, and documentation fixes are welcome. Please open issues or pull requests; for larger changes, open an issue first to discuss the plan.

## License

This repository is licensed under the MIT License — see the bundled `LICENSE` file for details.
