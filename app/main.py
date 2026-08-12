from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import DatabaseError
from starlette.responses import JSONResponse

from app.api.routes.posts import router as posts_router
from app.core.config import get_settings
from app.models import User  # noqa: F401  # pyright: ignore[reportUnusedImport]

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
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


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
