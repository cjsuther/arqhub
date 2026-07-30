"""Fixed-window rate limiter (SPEC §9/§12)."""

from app.core.ratelimit import RateLimiter


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_allows_up_to_limit_then_blocks():
    clock = FakeClock()
    rl = RateLimiter(limit=3, window=60.0, clock=clock)
    assert [rl.check("k") for _ in range(3)] == [True, True, True]
    assert rl.check("k") is False  # 4th over the limit


def test_window_resets():
    clock = FakeClock()
    rl = RateLimiter(limit=2, window=60.0, clock=clock)
    assert rl.check("k") and rl.check("k")
    assert rl.check("k") is False
    clock.t += 61  # new window
    assert rl.check("k") is True


def test_keys_are_independent():
    rl = RateLimiter(limit=1, window=60.0, clock=FakeClock())
    assert rl.check("a") is True
    assert rl.check("b") is True
    assert rl.check("a") is False
