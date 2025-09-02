from __future__ import annotations

import pytest

from nexus_agent.agent_loop import _retry


def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    """No-op sleep for fast tests."""
    return None


def _fixed_jitter(a: float, b: float) -> float:  # noqa: ARG001
    """Return deterministic jitter for tests."""
    return 1.0


class _Flaky:
    def __init__(self, fail_times: int, result: int) -> None:
        self.fail_times = fail_times
        self.calls = 0
        self.result = result

    def __call__(self) -> int:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("boom")
        return self.result


@pytest.fixture(autouse=True)
def patch_timers(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch time.sleep and random.uniform used by _retry
    import random as _random  # noqa: WPS433
    import time as _time  # noqa: WPS433

    monkeypatch.setattr(_time, "sleep", _no_sleep)
    monkeypatch.setattr(_random, "uniform", _fixed_jitter)


def test_retry_succeeds_after_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    flaky = _Flaky(fail_times=2, result=42)
    out = _retry(flaky, attempts=3, base_delay=0.01)
    assert out == 42
    assert flaky.calls == 3


def test_retry_exhausts_and_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    flaky = _Flaky(fail_times=5, result=7)
    with pytest.raises(RuntimeError):
        _retry(flaky, attempts=3, base_delay=0.01)
    assert flaky.calls == 3
