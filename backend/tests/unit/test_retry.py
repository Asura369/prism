from __future__ import annotations

import pytest

from prism.errors import RetryExhausted
from prism.retry import ServerError, retry_with_backoff


def test_transient_error_is_retried():
    calls = {"n": 0}

    @retry_with_backoff(attempts=3, base=0.001, factor=2, jitter=False, retry_on=(ServerError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ServerError("temporary")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_non_retryable_fails_immediately():
    calls = {"n": 0}

    @retry_with_backoff(attempts=3, base=0.001, factor=2, jitter=False, retry_on=(ServerError,))
    def bad_request():
        calls["n"] += 1
        raise ValueError("400 bad request")

    with pytest.raises(ValueError):
        bad_request()
    assert calls["n"] == 1


def test_retries_exhausted_raises_typed_error():
    calls = {"n": 0}

    @retry_with_backoff(attempts=2, base=0.001, factor=2, jitter=False, retry_on=(ServerError,), label="test-adapter")
    def always_fails():
        calls["n"] += 1
        raise ServerError("nope")

    with pytest.raises(RetryExhausted):
        always_fails()
    assert calls["n"] == 2
