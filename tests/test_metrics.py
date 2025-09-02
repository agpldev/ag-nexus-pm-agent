import random
import time

import pytest

from nexus_agent import metrics
from nexus_agent.agent_loop import TokenBucket, _retry
from nexus_agent.errors import is_retryable


def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    pass


def _fixed_jitter(a: float, b: float) -> float:  # noqa: ARG001
    return 1.0


class _Flaky:
    def __init__(self, fail_times: int, result: int) -> None:
        self.fail_times = fail_times
        self.calls = 0
        self.result = result

    def __call__(self) -> int:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient")
        return self.result


class _Always:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def __call__(self) -> int:
        raise self.exc


def setup_function() -> None:  # noqa: D401 - used by pytest
    """Reset metrics before each test."""
    metrics.reset()


def test_retry_counters_increment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "sleep", _no_sleep)
    monkeypatch.setattr(random, "uniform", _fixed_jitter)
    fn = _Flaky(fail_times=2, result=7)
    out = _retry(fn, attempts=3, base_delay=0.01, retry_if=is_retryable)
    assert out == 7
    snap = metrics.snapshot()
    # two retries happened
    assert snap.retries == 2
    assert snap.retry_exhausted == 0


def test_retry_exhausted_increments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "sleep", _no_sleep)
    monkeypatch.setattr(random, "uniform", _fixed_jitter)
    fn = _Always(ValueError("permanent"))
    with pytest.raises(ValueError):
        _retry(fn, attempts=3, base_delay=0.01, retry_if=is_retryable)
    snap = metrics.snapshot()
    # immediate non-retryable; counts as exhausted once
    assert snap.retry_exhausted == 1
    # no retries logged
    assert snap.retries == 0


def test_rate_limit_sleep_accumulates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Control monotonic and ensure we start with zero tokens to force a sleep
    fake_now = 1000.0

    def fake_monotonic() -> float:
        return fake_now

    def advance_time(seconds: float) -> None:
        nonlocal fake_now
        fake_now += seconds

    monkeypatch.setattr(time, "monotonic", fake_monotonic)
    monkeypatch.setattr(time, "sleep", advance_time)

    bucket = TokenBucket(rate=1.0, capacity=1.0)
    # Drain tokens
    bucket.tokens = 0.0

    bucket.consume(1.0)
    snap = metrics.snapshot()
    # Needed 1 token at 1 rps -> 1.0s sleep recorded
    assert snap.rate_limit_sleeps_total_s == pytest.approx(1.0, rel=1e-6)


def test_task_counters_direct() -> None:
    # Direct counters check (integration covered elsewhere)
    metrics.inc_tasks_created()
    metrics.inc_tasks_created()
    metrics.inc_tasks_skipped_dedupe()
    snap = metrics.snapshot()
    assert snap.tasks_created == 2
    assert snap.tasks_skipped_dedupe == 1
