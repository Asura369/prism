from __future__ import annotations

from typing import Any

from ..config import Config, Secrets, get_secrets
from ..errors import AdapterUnavailable
from .base import BaseAdapter, CardRendererAdapter, ImageSequenceExportAdapter, LLMAdapter
from .cards.templated import TemplatedCardRenderer
from .assembly.zip import ZipExportAdapter
from .llm.fake import FakeLLM
from .llm.openai import OpenAIAdapter

INTERFACES = ("llm", "cards", "export", "news")


class AdapterResolver:
    """Resolves config adapter names to available instances, honoring fallback chains."""

    def __init__(self, cfg: Config, secrets: Secrets | None = None):
        self.cfg = cfg
        self.secrets = secrets or get_secrets()
        self.fallbacks_used: list[str] = []
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
            "news": {},
        }
        if self.secrets.fake_adapters:
            self._registry["llm"] = {"fake": self._registry["llm"]["fake"]}
            self._registry["news"] = {}

    def chain_names(self, interface: str) -> list[str]:
        if interface == "llm" and self.secrets.fake_adapters:
            return ["fake"]
        if interface == "llm":
            return [self.cfg.adapters.llm.default, *self.cfg.adapters.llm.fallback]
        if interface == "cards":
            return [self.cfg.adapters.cards.default, *self.cfg.adapters.cards.fallback]
        if interface == "export":
            return [self.cfg.adapters.export.default]
        if interface == "news":
            return ["google_news_rss", "manual"]
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

    def use(self, interface: str) -> tuple[BaseAdapter, bool]:
        """Return the primary adapter plus whether a fallback was used."""
        chain = self.require(interface)
        chosen = chain[0]
        default_name = self.chain_names(interface)[0]
        used_fallback = getattr(chosen, "name", None) != default_name
        if used_fallback:
            label = f"{interface}:{chosen.name}"
            if label not in self.fallbacks_used:
                self.fallbacks_used.append(label)
        return chosen, used_fallback

    def availability(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for interface in INTERFACES:
            out[interface] = [
                {"name": name, "available": adapter.is_available()}
                for name, adapter in self.registered(interface).items()
            ]
        return out

    def llm_model(self) -> str | None:
        chain = self.resolve("llm")
        if not chain:
            return None
        model = getattr(chain[0], "model", None)
        return str(model) if model else chain[0].name

    def style_names(self) -> list[str]:
        cards = self.registered("cards").get(self.cfg.adapters.cards.default)
        if isinstance(cards, CardRendererAdapter):
            return cards.available_styles()
        return []
