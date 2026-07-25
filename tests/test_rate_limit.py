from loyalty_analytics.rate_limit import SlidingWindowRateLimiter


def test_rate_limiter_rejects_requests_over_limit() -> None:
    limiter = SlidingWindowRateLimiter()

    assert limiter.check("client", limit=2, window_seconds=60) is None
    assert limiter.check("client", limit=2, window_seconds=60) is None
    assert limiter.check("client", limit=2, window_seconds=60) is not None


def test_rate_limiter_tracks_clients_independently() -> None:
    limiter = SlidingWindowRateLimiter()

    assert limiter.check("client-a", limit=1, window_seconds=60) is None
    assert limiter.check("client-a", limit=1, window_seconds=60) is not None
    assert limiter.check("client-b", limit=1, window_seconds=60) is None


def test_rate_limiter_can_be_cleared() -> None:
    limiter = SlidingWindowRateLimiter()
    assert limiter.check("client", limit=1, window_seconds=60) is None
    assert limiter.check("client", limit=1, window_seconds=60) is not None

    limiter.clear()

    assert limiter.check("client", limit=1, window_seconds=60) is None
