"""Bound requests before multipart parsing; rate keys use the ASGI peer, not raw headers."""

import asyncio
import time
from collections import OrderedDict
from typing import cast

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings


class RequestLimits:
    def __init__(self, settings: Settings):
        self.read_limit: int = settings.api_read_limit
        self.write_limit: int = settings.api_write_limit
        self.buckets: OrderedDict[tuple[str, bool], tuple[float, int]] = OrderedDict()

    def allow(self, peer: str, write: bool) -> bool:
        now = time.monotonic()
        key = (peer, write)
        start, count = self.buckets.pop(key, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        allowed = count < (self.write_limit if write else self.read_limit)
        self.buckets[key] = (start, count + 1 if allowed else count)
        # Bound memory even when trusted ingress presents many distinct clients.
        if len(self.buckets) > 10000:
            _ = self.buckets.popitem(last=False)
        return allowed


class RequestGuard:
    def __init__(self, app: ASGIApp, limits: RequestLimits, max_bytes: int, timeout: float):
        self.app: ASGIApp = app
        self.limits: RequestLimits = limits
        self.max_bytes: int = max_bytes
        self.timeout: float = timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        async def reject(status: int, detail: str) -> None:
            response = JSONResponse({'detail': detail}, status_code=status,
                                    headers={'Retry-After': '60'} if status == 429 else None)
            await response(scope, receive, send)

        method = cast(str, scope.get('method', 'GET'))
        # Liveness/readiness must remain observable under user traffic limits.
        if scope.get('path') not in {'/health', '/ready'} and method != 'OPTIONS':
            peer = cast(tuple[str, int] | None, scope.get('client'))
            if not self.limits.allow(str(peer[0]) if peer else 'unknown', method not in {'GET', 'HEAD'}):
                await reject(429, 'Too many requests. Please try again later.')
                return
        for name, value in Headers(scope=scope).items():
            if name.lower() == 'content-length':
                try:
                    length = int(value)
                except ValueError:
                    await reject(400, 'Invalid Content-Length')
                    return
                if length < 0:
                    await reject(400, 'Invalid Content-Length')
                    return
                if length > self.max_bytes:
                    await reject(413, 'Request body too large')
                    return
        # Buffer at most the fixed envelope budget, before Starlette can spool
        # arbitrary file parts. No private parser APIs or leaked temporary files.
        body = bytearray()
        try:
            async with asyncio.timeout(self.timeout):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    if message['type'] != 'http.request':
                        continue
                    chunk = cast(bytes, message.get('body', b''))
                    if len(body) + len(chunk) > self.max_bytes:
                        await reject(413, 'Request body too large')
                        return
                    body.extend(chunk)
                    if not message.get('more_body', False):
                        break
        except TimeoutError:
            await reject(408, 'Request body timed out')
            return
        payload = bytes(body)
        del body
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': payload, 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)
