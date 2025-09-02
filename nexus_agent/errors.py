"""Error taxonomy and retryability predicates for agent components.

Defines helpers to determine whether an exception is likely transient (retryable)
or permanent (non-retryable). This is intentionally conservative to avoid
retrying on clearly permanent errors such as bad input or auth failures.
"""

from __future__ import annotations

from typing import Final

_RETRYABLE_EXC_TYPES: Final = (
    TimeoutError,
    ConnectionError,
)

_NON_RETRYABLE_EXC_TYPES: Final = (
    ValueError,
    PermissionError,
)


def is_retryable(exc: Exception) -> bool:
    """Return True if the exception is likely transient.

    Heuristics:
    - Retry on timeouts and connection errors
    - Do not retry on obvious programming/permission errors
    - Default: retry on RuntimeError (often used for transient API failures in code)
    """
    if isinstance(exc, _NON_RETRYABLE_EXC_TYPES):
        return False
    if isinstance(exc, _RETRYABLE_EXC_TYPES):
        return True
    return bool(isinstance(exc, RuntimeError))
