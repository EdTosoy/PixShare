# Architecture

This document describes the high-level architecture and runtime flow of PixShare.

## Overview

PixShare is a small full-stack media-sharing application composed of:

- A FastAPI asynchronous backend (app/) that exposes a REST API for creating, retrieving, updating, and deleting media posts.
- A Next.js frontend (web/) that demonstrates listing posts and performing authenticated uploads.
- A storage abstraction layer allowing uploads to be stored either on the local filesystem (dev) or an S3-compatible object store (prod).
- PostgreSQL as the primary persistence store, with Alembic for schema migrations.

The application focuses on secure file upload patterns: validating file types and contents, enforcing per-user ownership, and ensuring safe replacement and cleanup of media objects.

## Components

- API (FastAPI)
  - Entrypoint: `app/main.py` mounts the FastAPI app, serves static uploads at `/uploads`, and wires dependencies.
  - Routes: `app/api/routes/posts.py` (post CRUD + safe file lifecycle), `app/api/routes/auth.py` (authentication endpoints).
  - Dependencies: `app/api/dependencies.py` exposes DI for current user, db session, and storage backend.

- Storage
  - Abstraction: `app/storage/` defines an interface for upload, delete, and other operations.
  - Local backend: stores files under `UPLOADS_DIR` and serves them as static files for development.
  - S3 backend: a production-ready option that uploads objects to an S3-compatible bucket and returns object URLs.

- Persistence
  - SQLAlchemy (async) models under `app/models/` (User, Post).
  - `app/db/` contains session setup and Base model wiring.
  - Alembic for migrations (migrations/ and alembic.ini).

- Frontend
  - `web/` holds a Next.js app that consumes the API. It's intentionally minimal to keep focus on backend patterns.

## Runtime flow (create post)

1. Client issues POST /posts with a multipart form: file + caption.
2. FastAPI route receives `UploadFile` and first calls `app/core/upload.validate_upload` to check content type, size, and verify image using Pillow.
3. The storage dependency's `upload` method is called to persist the bytes (local or S3). It returns a public URL.
4. A new Post record is created and added to the DB session, then the session is committed and refreshed.
5. On success, the new Post is returned. On failure after upload but before commit, the code removes the new object to avoid orphaned files.

## Runtime flow (replace post file)

1. Client issues PATCH /posts/{id} with a new file.
2. Server validates new file and uploads it (new_url).
3. The Post object is updated with new_url and DB commit is attempted.
4. If commit succeeds, old file is deleted from storage. If commit fails, the new file is deleted and the DB remains unchanged.

## Security considerations

- Files are validated by MIME type against an allowed list and verified with Pillow to prevent spoofing.
- File size is bounded by MAX_FILE_SIZE (10 MB) to avoid large uploads.
- Ownership checks ensure only the creator can update/delete their posts.
- Storage keys/URLs should be unguessable in production or served via signed URLs; local dev uses a simple static mount.

## Observability and metrics (suggested)

- Expose a `/health` endpoint for readiness/liveness checks.
- Add basic request/response metrics (Prometheus) and error logging (Sentry).

## Deployment notes

- Use environment variables for configuration (DATABASE_URL, S3 credentials, SECRET_KEY).
- Migrate DB on deploy (alembic upgrade head).
- Use a CDN in front of object storage for production performance.

## Files to inspect
- `app/main.py` — app wiring and static mounts
- `app/api/routes/posts.py` — upload/create/replace/delete flows
- `app/core/upload.py` — validation logic
- `app/storage/` — storage backends
- `migrations/` + `alembic.ini` — migration config
