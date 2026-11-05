from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..config import Config
from ..errors import AdapterUnavailable
from ..providers.config import effective_llm, stub_only_enabled
from .base import BaseAdapter, CardRendererAdapter
from .cards.templated import TemplatedCardRenderer
from .assembly.zip import ZipExportAdapter
from .llm.stub import StubLLM
from .llm.openai import OpenAIAdapter
from .news.stub import StubNews
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

    def __init__(self, cfg: Config, *, db_path: str | None = None, stub_only: bool | None = None):
        self.cfg = cfg
        self.db_path = db_path
        self._forced_stub = stub_only
        self._llm_name = "stub"
        self._registry: dict[str, dict[str, BaseAdapter]] = {
            "llm": {},
            "cards": {
                "templated": TemplatedCardRenderer(cfg),
            },
            "export": {
                "zip": ZipExportAdapter(),
            },
            "news": {
                "google_news_rss": GoogleNewsRSSNews(),
                "stub": StubNews(),
            },
        }
        self.refresh_llm()

    def stub_only(self) -> bool:
        """Testing mode: forced for this instance (tests, demo), else the stored setting."""
        if self._forced_stub is not None:
            return self._forced_stub
        return stub_only_enabled(self.db_path)

    def refresh_llm(self) -> None:
        """Rebuild the LLM adapter from the stored provider; called per job and after writes."""
        effective = None if self.stub_only() else effective_llm(self.db_path)
        if effective is None:
            self._llm_name = "stub"
            self._registry["llm"] = {"stub": StubLLM()}
            return
        adapter = OpenAIAdapter(effective.config, api_key=effective.api_key, name=effective.provider)
        self._llm_name = effective.provider
        self._registry["llm"] = {effective.provider: adapter, "stub": StubLLM()}

    @property
    def llm_name(self) -> str:
        """The adapter a healthy run is expected to use (provenance and degraded checks)."""
        return self._llm_name

    def chain_names(self, interface: str) -> list[str]:
        if interface in ("llm", "news") and self.stub_only():
            return ["stub"]
        if interface == "llm":
            names = [self._llm_name] if self._llm_name == "stub" else [self._llm_name, "stub"]
            return list(dict.fromkeys(names))
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
        """The chain each interface would actually try, in order — not just what is registered."""
        out: dict[str, list[dict[str, Any]]] = {}
        for interface in INTERFACES:
            registered = self.registered(interface)
            out[interface] = [
                {
                    "name": name,
                    "available": registered[name].is_available() if name in registered else False,
                }
                for name in self.chain_names(interface)
            ]
        return out

    def style_names(self) -> list[str]:
        cards = self.registered("cards").get(self.cfg.adapters.cards.default)
        if isinstance(cards, CardRendererAdapter):
            return cards.available_styles()
        return []
