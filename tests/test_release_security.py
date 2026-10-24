import asyncio
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.request_guard import RequestGuard, RequestLimits
from app.main import app, readiness_check
from tests.conftest import test_engine
from tests.helpers.settings import IsolatedSettings


def production_settings(**overrides: object):
    values: dict[str, object] = {'database_url': 'postgresql+asyncpg://localhost/security_test', 'environment': 'production',
        'clerk_secret_key': 'sk_live_unit_placeholder', 'cors_origins': ['https://app.example.test'],
        'clerk_authorized_parties': ['https://app.example.test'], 'allowed_hosts': ['api.example.test']}
    values.update(overrides)
    return IsolatedSettings.model_validate(values)


@pytest.mark.parametrize('overrides', [
    {'clerk_authorized_parties': []}, {'cors_origins': ['*']},
    {'cors_origins': ['http://app.example.test']}, {'clerk_authorized_parties': ['https://other.example.test']},
    {'cors_origins': ['https://app.example.test/path']}, {'allowed_hosts': ['*']},
    {'clerk_secret_key': 'sk_test_never_live'}, {'clerk_secret_key': ''},
])
def test_production_refuses_unsafe_configuration(overrides: dict[str, object]):
    with pytest.raises(ValueError):
        _ = production_settings(**overrides)


def test_valid_explicit_production_config():
    assert production_settings().environment == 'production'


@pytest.mark.asyncio
async def test_body_limits_count_streamed_bytes_and_ignore_false_headers():
    settings = IsolatedSettings(database_url='postgresql://localhost/security_test')
    limited = FastAPI()
    limited.add_middleware(RequestGuard, limits=RequestLimits(settings), max_bytes=8, timeout=0.1)

    @limited.post('/')
    async def echo(request: Request):
        return {'length': len(await request.body())}

    _ = echo

    async def chunks() -> AsyncIterator[bytes]:
        yield b'12345'
        yield b'67890'

    async with AsyncClient(transport=ASGITransport(app=limited), base_url='http://test') as client:
        assert (await client.post('/', content=b'12345678')).json() == {'length': 8}
        assert (await client.post('/', content=b'123456789')).status_code == 413
        assert (await client.post('/', content=chunks())).status_code == 413
        assert (await client.post('/', content=chunks(), headers={'Content-Length': '1'})).status_code == 413
        assert (await client.post('/', content=b'', headers={'Content-Length': '-1'})).status_code == 400


@pytest.mark.asyncio
async def test_slow_request_deadline():
    settings = IsolatedSettings(database_url='postgresql://localhost/security_test')
    limited = FastAPI()
    limited.add_middleware(RequestGuard, limits=RequestLimits(settings), max_bytes=8, timeout=0.01)

    async def slow() -> AsyncIterator[bytes]:
        yield b'1'
        await asyncio.sleep(0.1)
        yield b'2'

    async with AsyncClient(transport=ASGITransport(app=limited), base_url='http://test') as client:
        assert (await client.post('/', content=slow())).status_code == 408


@pytest.mark.asyncio
async def test_rate_limits_do_not_trust_forwarded_headers():
    settings = IsolatedSettings(database_url='postgresql://localhost/security_test', api_write_limit=2)
    limited = FastAPI()
    limits = RequestLimits(settings)
    limited.add_middleware(RequestGuard, limits=limits, max_bytes=8, timeout=1)

    @limited.post('/')
    async def okay():
        return {'ok': True}

    _ = okay

    async with AsyncClient(transport=ASGITransport(app=limited), base_url='http://test') as client:
        assert (await client.post('/')).status_code == 200
        assert (await client.post('/')).status_code == 200
        response = await client.post('/', headers={'X-Forwarded-For': 'fake-new-address'})
        assert response.status_code == 429 and response.headers['Retry-After'] == '60'
    # Floods of different peers cannot grow the table beyond its fixed budget.
    for number in range(10002):
        _ = limits.allow(str(number), False)
    assert len(limits.buckets) == 10000


@pytest.mark.asyncio
async def test_ready_probes_isolated_database_and_failures_are_generic():
    with patch('app.main.engine', test_engine):
        assert (await readiness_check()).status_code == 200
    with patch.object(AsyncEngine, 'connect', side_effect=OSError('private database diagnostic')):
        response = await readiness_check()
    assert response.status_code == 503 and b'private' not in response.body


@pytest.mark.asyncio
async def test_untrusted_hosts_and_cookie_only_api_auth_are_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://untrusted.example') as client:
        assert (await client.get('/health')).status_code == 400
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/users/me', headers={'Cookie': '__session=not-a-bearer-session'})
        assert response.status_code == 401
        assert response.headers['WWW-Authenticate'] == 'Bearer'
