"""Fixed-window request counter in Valkey (SPEC Section 9, rule 6)."""

import logging
import time
from functools import lru_cache

import redis
from fastapi import Request

from app.config import get_settings
from app.errors import Problem

log = logging.getLogger(__name__)

WINDOW_SECONDS = 60


@lru_cache
def get_valkey() -> redis.Redis:
    return redis.Redis.from_url(
        get_settings().valkey_url, socket_timeout=0.5, socket_connect_timeout=0.5
    )


def enforce_auth_rate_limit(request: Request, scope: str) -> None:
    limit = get_settings().auth_rate_limit_per_minute
    ip = request.client.host if request.client else "unknown"
    window = int(time.time()) // WINDOW_SECONDS
    key = f"ratelimit:{scope}:{ip}:{window}"
    try:
        pipe = get_valkey().pipeline()
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS)
        count = pipe.execute()[0]
    except redis.RedisError:
        # D-006: if Valkey is down, sign-in keeps working without the limit.
        log.warning("rate limiter unavailable; allowing %s request", scope)
        return
    if count > limit:
        raise Problem(
            429,
            "Too many requests",
            "Too many attempts. Wait a minute and try again.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )
