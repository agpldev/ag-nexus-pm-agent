from __future__ import annotations

import pytest

from nexus_agent.agent_loop import TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_token_bucket_allows_initial_burst(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()

    # Patch time.monotonic and time.sleep inside module under test
    import time as _time

    monkeypatch.setattr(_time, "monotonic", clock.monotonic)

    tb = TokenBucket(rate=2.0, capacity=3)  # 3 initial tokens
    # Initial consumes should not sleep
    tb.consume()
    tb.consume()
    tb.consume()

    # No tokens left; advance time by 0.5s -> +1 token at 2 rps yields 1 token after 0.5s
    slept: list[float] = []

    def fake_sleep(sec: float) -> None:
        slept.append(sec)
        clock.advance(sec)

    monkeypatch.setattr(_time, "sleep", fake_sleep)

    tb.consume()  # will sleep ~0.5s to earn one token
    assert pytest.approx(sum(slept), rel=1e-3) == 0.5


def test_token_bucket_refill_over_time(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()
    import time as _time

    monkeypatch.setattr(_time, "monotonic", clock.monotonic)

    tb = TokenBucket(rate=1.0, capacity=1)
    # Use initial token
    tb.consume()

    slept: list[float] = []

    def fake_sleep(sec: float) -> None:
        slept.append(sec)
        clock.advance(sec)

    monkeypatch.setattr(_time, "sleep", fake_sleep)

    # Need to wait ~1s for next token
    tb.consume()
    assert pytest.approx(sum(slept), rel=1e-3) == 1.0
