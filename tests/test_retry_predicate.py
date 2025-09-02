from __future__ import annotations

import pytest

from nexus_agent.agent_loop import _retry
from nexus_agent.errors import is_retryable


def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    return None


def _fixed_jitter(a: float, b: float) -> float:  # noqa: ARG001
    return 1.0


class _AlwaysRaises:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        raise self.exc


class _FlakyRuntime:
    def __init__(self, fail_times: int, result: int) -> None:
        self.fail_times = fail_times
        self.calls = 0
        self.result = result

    def __call__(self) -> int:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient")
        return self.result


@pytest.fixture(autouse=True)
def patch_timers(monkeypatch: pytest.MonkeyPatch) -> None:
    import random as _random
    import time as _time

    monkeypatch.setattr(_time, "sleep", _no_sleep)
    monkeypatch.setattr(_random, "uniform", _fixed_jitter)


def test_non_retryable_fails_immediately() -> None:
    func = _AlwaysRaises(ValueError("permanent"))
    with pytest.raises(ValueError):
        _retry(func, attempts=3, base_delay=0.01, retry_if=is_retryable)
    # Only first call executed; no retries
    assert func.calls == 1


def test_retryable_runtime_retries_and_succeeds() -> None:
    func = _FlakyRuntime(fail_times=2, result=99)
    out = _retry(func, attempts=3, base_delay=0.01, retry_if=is_retryable)
    assert out == 99
    assert func.calls == 3
