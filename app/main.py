from fastapi import FastAPI

from app.api.routes.posts import router as posts_router
from app.core.config import get_settings
from app.models import User  # noqa: F401  # pyright: ignore[reportUnusedImport]

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(posts_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
