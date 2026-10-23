from typing import override

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class MediaFiles(StaticFiles):
    @override
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if path.startswith("_variants/") and path.endswith(".webp") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
