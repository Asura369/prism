from __future__ import annotations

import time
from typing import Any

from ..adapters.resolver import AdapterResolver
from ..config import Config


def call_llm(
    cfg: Config,
    resolver: AdapterResolver,
    prompt: str,
    *,
    json_schema: dict[str, Any] | None = None,
) -> str:
    last_error: Exception | None = None
    for adapter in resolver.require("llm"):
        for attempt in range(1, cfg.run.max_retries + 1):
            try:
                return adapter.complete(prompt, json_schema=json_schema)  # type: ignore[union-attr]
            except Exception as exc:  # noqa: BLE001 - adapter boundary
                last_error = exc
                if attempt < cfg.run.max_retries:
                    backoff = cfg.run.retry_backoff_s
                    time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])
    raise last_error or RuntimeError("No LLM adapter produced output")
