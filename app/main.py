from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DatabaseError
from starlette.responses import JSONResponse

from app.api.routes import users
from app.api.routes.posts import router as posts_router
from app.core.config import get_settings
from app.models import User  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.storage.media import MediaFiles

settings = get_settings()

UPLOADS_DIR = Path(settings.uploads_dir)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)
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


@app.exception_handler(DatabaseError)
async def database_error_handler(
    request: Request,  # pyright: ignore[reportUnusedParameter]
    exc: DatabaseError,  # pyright: ignore[reportUnusedParameter]
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(posts_router)
app.include_router(users.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
