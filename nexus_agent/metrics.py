"""Lightweight in-process metrics counters for agent observability.

The counters are process-local and primarily intended for structured logging
and test assertions. For production telemetry, hook these into a backend.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Counters:
    retries: int = 0
    retry_exhausted: int = 0
    tasks_created: int = 0
    tasks_skipped_dedupe: int = 0
    rate_limit_sleeps_total_s: float = 0.0


_counters = Counters()


def inc_retries() -> None:
    _counters.retries += 1


def inc_retry_exhausted() -> None:
    _counters.retry_exhausted += 1


def inc_tasks_created() -> None:
    _counters.tasks_created += 1


def inc_tasks_skipped_dedupe() -> None:
    _counters.tasks_skipped_dedupe += 1


def add_rate_limit_sleep(seconds: float) -> None:
    _counters.rate_limit_sleeps_total_s += max(0.0, float(seconds))


def snapshot() -> Counters:
    """Return a copy-like view of counters for reporting/tests."""
    return Counters(
        retries=_counters.retries,
        retry_exhausted=_counters.retry_exhausted,
        tasks_created=_counters.tasks_created,
        tasks_skipped_dedupe=_counters.tasks_skipped_dedupe,
        rate_limit_sleeps_total_s=_counters.rate_limit_sleeps_total_s,
    )


def reset() -> None:
    """Reset counters (for tests)."""
    global _counters
    _counters = Counters()
