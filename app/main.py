import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from app.api.routes import users
from app.api.routes.posts import router as posts_router
from app.core.config import get_settings
from app.core.request_guard import RequestGuard, RequestLimits
from app.db.session import engine
from app.models import User  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.storage.base import StorageUnavailable
from app.storage.media import MediaFiles

settings = get_settings()

UPLOADS_DIR = Path(settings.uploads_dir)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)
request_limits = RequestLimits(settings)
app.add_middleware(RequestGuard, limits=request_limits, max_bytes=settings.api_max_body_bytes, timeout=settings.request_body_timeout)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/uploads",
    MediaFiles(directory=UPLOADS_DIR),
    name="uploads",
)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(
    request: Request,  # pyright: ignore[reportUnusedParameter]
    exc: SQLAlchemyError,  # pyright: ignore[reportUnusedParameter]
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(StorageUnavailable)
async def storage_error_handler(
    request: Request,  # pyright: ignore[reportUnusedParameter]
    exc: StorageUnavailable,  # pyright: ignore[reportUnusedParameter]
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Media storage is temporarily unavailable. Please try again."},
    )


app.include_router(posts_router)
app.include_router(users.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check() -> JSONResponse:
    try:
        async with asyncio.timeout(settings.readiness_timeout):
            async with engine.connect() as connection:
                _ = await connection.execute(text("SELECT 1"))
                # An empty/unmigrated DB must not be declared ready.
                _ = await connection.execute(text("SELECT id FROM posts LIMIT 0"))
                _ = await connection.execute(text("SELECT id FROM users LIMIT 0"))
        return JSONResponse({"status": "ready"})
    except Exception:  # noqa: BLE001 - no database diagnostics in public readiness output
        return JSONResponse({"status": "unavailable"}, status_code=503)
