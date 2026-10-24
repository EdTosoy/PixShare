import pytest
from sqlalchemy.engine import make_url

from scripts.render_start import database_url, port


@pytest.mark.parametrize("driver", ["postgres", "postgresql", "postgresql+asyncpg"])
def test_render_url_preserves_escaped_password_and_requires_tls(driver: str):
    parsed = make_url(database_url(f"{driver}://test:p%40ss%2Fword@db/staging"))
    assert parsed.drivername == "postgresql+asyncpg"
    assert parsed.password == "p@ss/word"
    assert parsed.query == {"ssl": "require"}


def test_render_url_preserves_explicit_certificate_verification():
    parsed = make_url(database_url(
        "postgresql://test:example@db/staging?sslmode=verify-full&application_name=staging",
    ))
    assert parsed.query == {"ssl": "verify-full", "application_name": "staging"}


@pytest.mark.parametrize("value", [
    "sqlite:///test", "postgresql://db/staging?ssl=disable",
    "postgresql://db/staging?ssl=require&sslmode=verify-full",
])
def test_render_url_rejects_unsafe_or_ambiguous_configuration(value: str):
    with pytest.raises(ValueError):
        _ = database_url(value)


@pytest.mark.parametrize("value", ["0", "65536", "invalid"])
def test_invalid_port(value: str):
    with pytest.raises(ValueError):
        _ = port(value)


def test_render_default_port():
    assert port("10000") == "10000"
