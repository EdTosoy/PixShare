"""Render launch adapter. Never print connection strings or private settings."""

import os
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def database_url(value: str) -> str:
    """Render's internal PostgreSQL TLS encrypts without CA verification.

    External connections should explicitly supply ssl=verify-full instead.
    This conversion belongs to the Render adapter, not generic app settings.
    """
    url = make_url(value)
    if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
        raise ValueError("Expected PostgreSQL")
    query = dict(url.query)
    if "ssl" in query and "sslmode" in query:
        raise ValueError("Conflicting TLS settings")
    tls = query.pop("sslmode", query.get("ssl", "require"))
    if tls not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("TLS must be enabled")
    query["ssl"] = tls
    return url.set(drivername="postgresql+asyncpg", query=query).render_as_string(
        hide_password=False,
    )


def port(value: str) -> str:
    number = int(value)
    if not 1 <= number <= 65535:
        raise ValueError("Invalid port")
    return str(number)


def main() -> None:
    try:
        os.environ["DATABASE_URL"] = database_url(os.environ["DATABASE_URL"])
        listen_port = port(os.environ.get("PORT", "10000"))
    except (ArgumentError, KeyError, ValueError, TypeError):
        raise SystemExit("Invalid Render database or port configuration") from None
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0",
        "--port", listen_port, "--no-access-log", "--limit-concurrency", "8",
        "--backlog", "128", "--timeout-keep-alive", "5",
        "--timeout-graceful-shutdown", "30",
    ])


if __name__ == "__main__":
    main()
