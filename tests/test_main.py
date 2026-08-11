import pytest
from fastapi import Request
from sqlalchemy.exc import DatabaseError

from app.main import database_error_handler


@pytest.mark.asyncio
async def test_database_error_handler_returns_500():
    exc = DatabaseError(
        "statement",
        {},
        Exception("database failed"),
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1234),
            "scheme": "http",
        }
    )

    response = await database_error_handler(
        request=request,
        exc=exc,
    )

    assert response.status_code == 500
    assert response.body == b'{"detail":"Internal server error"}'
