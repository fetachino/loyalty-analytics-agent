import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from loyalty_analytics.config import get_settings


class SlidingWindowRateLimiter:
    """Thread-safe, per-client sliding-window limiter for a single API process."""

    def __init__(self) -> None:
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int | None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, round(window_seconds - (now - timestamps[0])))
                return retry_after
            timestamps.append(now)
        return None

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


agent_rate_limiter = SlidingWindowRateLimiter()


def enforce_agent_rate_limit(request: Request) -> None:
    settings = get_settings()
    client_host = request.client.host if request.client else "unknown"
    retry_after = agent_rate_limiter.check(
        client_host,
        settings.agent_rate_limit_requests,
        settings.agent_rate_limit_window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI agent rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
