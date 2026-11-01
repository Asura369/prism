from __future__ import annotations

import httpx

from ...adapters.base import TrendSourceAdapter
from ...config import Config
from .google_news import GoogleNewsRSS
from .hackernews import HackerNewsTop

FETCHABLE = ("google_news_rss", "hackernews")


def build_sources(cfg: Config, client: httpx.Client | None = None) -> dict[str, TrendSourceAdapter]:
    """Network-backed trend sources only; CSV/manual enter through their own endpoints."""
    timeout_s = cfg.discovery.fetch_timeout_s
    sources: dict[str, TrendSourceAdapter] = {}
    if cfg.discovery.sources.google_news_rss.enabled:
        sources["google_news_rss"] = GoogleNewsRSS(timeout_s=timeout_s, client=client)
    if cfg.discovery.sources.hackernews.enabled:
        sources["hackernews"] = HackerNewsTop(timeout_s=timeout_s, client=client)
    return sources


def enabled_fetchable(cfg: Config) -> list[str]:
    return [name for name in FETCHABLE if getattr(cfg.discovery.sources, name).enabled]
