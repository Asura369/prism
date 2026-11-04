from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..config import Config, Secrets, get_secrets
from ..errors import AdapterUnavailable
from .base import BaseAdapter, CardRendererAdapter
from .cards.templated import TemplatedCardRenderer
from .assembly.zip import ZipExportAdapter
from .llm.fake import FakeLLM
from .llm.openai import OpenAIAdapter
from .news.fake import FakeNews
from .news.google_news import GoogleNewsRSSNews

INTERFACES = ("llm", "cards", "export", "news")


@dataclass
class Completion:
    text: str
    adapter: str
    model: str
    failures: list[dict[str, Any]]


class AdapterResolver:
    """Resolves config adapter names to available instances, honoring fallback chains."""

    def __init__(self, cfg: Config, secrets: Secrets | None = None):
        self.cfg = cfg
        self.secrets = secrets or get_secrets()
        self._registry: dict[str, dict[str, BaseAdapter]] = {
            "llm": {
                "openai_compat": OpenAIAdapter(cfg.adapters.llm.openai_compat, self.secrets),
                "fake": FakeLLM(),
            },
            "cards": {
                "templated": TemplatedCardRenderer(cfg),
            },
            "export": {
                "zip": ZipExportAdapter(),
            },
            "news": {
                "google_news_rss": GoogleNewsRSSNews(),
                "fake": FakeNews(),
            },
        }
        if self.secrets.fake_adapters:
            self._registry["llm"] = {"fake": self._registry["llm"]["fake"]}
            self._registry["news"] = {"fake": self._registry["news"]["fake"]}

    def chain_names(self, interface: str) -> list[str]:
        if interface in ("llm", "news") and self.secrets.fake_adapters:
            return ["fake"]
        if interface == "llm":
            return [self.cfg.adapters.llm.default, *self.cfg.adapters.llm.fallback]
        if interface == "cards":
            return [self.cfg.adapters.cards.default]
        if interface == "export":
            return [self.cfg.adapters.export.default]
        if interface == "news":
            return ["google_news_rss"]
        raise AdapterUnavailable(interface, f"Unknown adapter interface: {interface}")

    def registered(self, interface: str) -> dict[str, BaseAdapter]:
        return self._registry.get(interface, {})

    def resolve(self, interface: str) -> list[BaseAdapter]:
        chain: list[BaseAdapter] = []
        for name in self.chain_names(interface):
            adapter = self.registered(interface).get(name)
            if adapter and adapter.is_available():
                chain.append(adapter)
        return chain

    def require(self, interface: str) -> list[BaseAdapter]:
        chain = self.resolve(interface)
        if not chain:
            raise AdapterUnavailable(interface, f"No available adapter for '{interface}'")
        return chain

    def get(self, interface: str) -> BaseAdapter:
        return self.require(interface)[0]

    def complete(self, prompt: str, *, json_schema: dict[str, Any] | None = None) -> Completion:
        """Call the first adapter in the LLM chain that answers, retrying transient failures."""
        failures: list[dict[str, Any]] = []
        last_error: Exception | None = None
        for adapter in self.require("llm"):
            for attempt in range(1, self.cfg.run.max_retries + 1):
                try:
                    text = adapter.complete(prompt, json_schema=json_schema)  # type: ignore[union-attr]
                    name = getattr(adapter, "name", "unknown")
                    return Completion(text, name, str(getattr(adapter, "model", name)), failures)
                except Exception as exc:  # noqa: BLE001 - adapter boundary
                    last_error = exc
                    failures.append(
                        {"adapter": getattr(adapter, "name", "?"), "attempt": attempt, "error": str(exc)}
                    )
                    if attempt < self.cfg.run.max_retries:
                        backoff = self.cfg.run.retry_backoff_s
                        time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])
        raise last_error or RuntimeError("No LLM adapter produced output")

    def availability(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for interface in INTERFACES:
            out[interface] = [
                {"name": name, "available": adapter.is_available()}
                for name, adapter in self.registered(interface).items()
            ]
        return out

    def style_names(self) -> list[str]:
        cards = self.registered("cards").get(self.cfg.adapters.cards.default)
        if isinstance(cards, CardRendererAdapter):
            return cards.available_styles()
        return []
