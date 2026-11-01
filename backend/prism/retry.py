from __future__ import annotations

from typing import Any, Callable

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .errors import RetryExhausted


class RateLimitError(Exception):
    def __init__(self, message: str, retry_after_s: float | None = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class ServerError(Exception):
    pass


RETRYABLE_EXC = (httpx.TimeoutException, httpx.NetworkError, RateLimitError, ServerError)


def retry_with_backoff(
    attempts: int = 3,
    base: float = 1,
    factor: float = 4,
    jitter: bool = True,
    retry_on: tuple[type[Exception], ...] = RETRYABLE_EXC,
    label: str = "adapter",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Retry transient failures with exponential backoff; re-raise everything else immediately."""

    def _raise_exhausted(state: RetryCallState) -> None:
        cause = state.outcome.exception() if state.outcome else None
        raise RetryExhausted(label, state.attempt_number) from cause

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        wrapped = retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential_jitter(initial=base, exp_base=factor, max=base * factor ** (attempts - 1), jitter=base if jitter else 0),
            retry=retry_if_exception_type(retry_on),
            retry_error_callback=_raise_exhausted,
            reraise=False,
        )(fn)
        return wrapped

    return decorator
