# PixShare

PixShare is a production-minded media sharing demo: a FastAPI async backend that enforces safe uploads, file verification, and ownership rules, paired with a minimal Next.js frontend. It demonstrates secure multipart uploads, storage abstraction (local filesystem or object storage), PostgreSQL persistence, Alembic migrations, and integration tests.

## Highlights

- FastAPI async backend with endpoints for post creation, retrieval, replacement, and deletion
- Server-side image validation and verification using Pillow (JPEG / PNG / WebP; max 10 MB)
- Storage backend abstraction (local filesystem or S3-compatible object storage)
- PostgreSQL persistence with Alembic migrations
- Minimal TypeScript Next.js frontend in `web/` demonstrating the API
- Integration tests and CI-ready configuration

## Key features

- Authentication and per-user ownership checks for create/update/delete operations
- Multipart file uploads handled safely with content verification (Pillow)
- Safe image replacement: upload new object first, commit DB, then remove old object; roll back and cleanup on failure
- Static upload serving mounted at `/uploads` (see `app/main.py`)
- Pagination, filtering, and sorting for post listing endpoints
- Idempotent demo database seeding with sample images

## Quickstart (recommended: Docker Compose)

The repository includes a Docker Compose configuration for local development and integration testing.

### 1. Clone the repository

```bash
git clone https://github.com/EdTosoy/PixShare.git
cd PixShare
```

### 2. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Set the required Clerk values in `.env`.

### 3. Start the application

Build and start the services:

```bash
docker compose up --build
```

The application will be available at:

- API: [http://localhost:8000](http://localhost:8000)
- Frontend: [http://localhost:3000](http://localhost:3000)
- API health check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run database migrations

In another terminal:

```bash
docker compose exec api uv run alembic upgrade head
```

### 5. Seed demo data

The repository includes three sample images under `demo/`. Seed them with:

```bash
docker compose exec api uv run python -m scripts.seed_db
```

The seed script creates the demo user, copies the sample images into the application's upload storage, and creates the corresponding database records. It is safe to run multiple times.

### 6. Open the frontend

Visit:

[http://localhost:3000](http://localhost:3000)

## Run the API locally (no Docker)

1. Create and activate a Python virtual environment.
2. Install dependencies using the project's package manager.
3. Ensure PostgreSQL is available.
4. Set the required environment variables.
5. Apply migrations and run the server.

Using `uv`:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Environment variables

See `app/core/config.py` for the exact configuration used by the API.

A sample `.env.example` is included in the repository.

The main variables are:

- `DATABASE_URL` — PostgreSQL connection string
- `CLERK_PUBLISHABLE_KEY` — Clerk publishable key
- `CLERK_SECRET_KEY` — Clerk secret key
- `CLERK_JWT_KEY` — Clerk JWT verification key, when configured
- `CLERK_AUTHORIZED_PARTIES` — comma-separated authorized frontend origins

The Next.js frontend has its own environment configuration under `web/.env.example`.

## API (selected endpoints)

Base URL: [http://localhost:8000](http://localhost:8000)

- `GET /posts`
  - Query params: `limit`, `offset`, `file_type`, `sort` (`newest` | `oldest`)
  - Returns a paginated list of posts

- `GET /posts/{post_id}`
  - Returns a single post by UUID

- `POST /posts`
  - Authenticated. Form multipart: `file` (image), `caption` (optional)
  - Validates image (JPEG/PNG/WEBP), uploads to storage, persists Post

- `PATCH /posts/{post_id}`
  - Authenticated and owner-only. Accepts a new file (optional) and caption
  - Safely replaces files: uploads the new object first and deletes the old object after DB commit; if the DB commit fails, the new upload is deleted

- `DELETE /posts/{post_id}`
  - Authenticated and owner-only. Deletes the storage object and database record

## Upload validation

Upload validation and verification are implemented in `app/core/upload.py` and enforce:

- Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`
- Maximum file size: 10 MB
- The server verifies the actual image format via Pillow, not just the declared content type

## Storage

Storage is abstracted under `app/storage/`.

The default development configuration uses local filesystem storage. Uploaded files are stored under `uploads/` and served at `/uploads`.

The storage layer is designed so that it can be replaced with an object store such as S3 without changing the post routes.

## Database & Migrations

Alembic is configured for database migrations. Migration scripts are located in `migrations/`, with configuration in `alembic.ini`.

Apply migrations with:

```bash
docker compose exec api uv run alembic upgrade head
```

## Demo data

Sample images are included under:

```text
demo/
├── sample_art.webp
├── sample_city.png
└── sample_sunset.jpg
```

Seed the database and copy the demo images into upload storage with:

```bash
docker compose exec api uv run python -m scripts.seed_db
```

The seed operation is idempotent and can safely be run again without creating duplicate users or posts.

## Tests

Integration tests are present under `tests/`.

Run the test suite locally with:

```bash
uv run pytest
```

Or inside the API container:

```bash
docker compose exec api uv run pytest
```

## Development notes

- The storage layer is abstracted under `app/storage/` so you can switch between local filesystem storage and an object store.
- Upload validation lives in `app/core/upload.py`.
- Post routes and safe replacement logic are in `app/api/routes/posts.py`.
- Authentication and current-user handling are implemented under `app/api/`.
- Database models are located under `app/models/`.
- Database migrations are managed with Alembic.
- The Next.js frontend is located under `web/`.

## Contributing

Contributions, issues, and documentation fixes are welcome. Please open an issue or pull request; for larger changes, open an issue first to discuss the plan.

## License

This repository is licensed under the MIT License — see the bundled `LICENSE` file for details.

```

```
