from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from shared.observability import inc_rate_limited


class InMemoryRateLimiter:
    def __init__(self, *, service_name: str, enabled: bool, limit: int, window_seconds: int) -> None:
        self.service_name = service_name
        self.enabled = enabled
        self.limit = max(limit, 1)
        self.window_seconds = max(window_seconds, 1)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        if not self.enabled:
            return True

        now = time.time()
        cutoff = now - self.window_seconds

        async with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.limit:
                return False

            bucket.append(now)
            return True


def client_identifier(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_write_rate_limit(request: Request) -> None:
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    key = f"{request.method}:{request.url.path}:{client_identifier(request)}"
    allowed = await limiter.allow(key)
    if allowed:
        return

    inc_rate_limited(limiter.service_name, request.url.path, request.method)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded",
    )
