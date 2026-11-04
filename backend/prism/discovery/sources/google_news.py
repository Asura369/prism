from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ...adapters.base import TrendSourceAdapter
from ...domain import TrendCandidate
from ...rss import fetch_feed


class GoogleNewsRSS(TrendSourceAdapter):
    name = "google_news_rss"

    def __init__(self, timeout_s: int = 10, client=None):
        self.timeout_s = timeout_s
        self.client = client

    def fetch(self, *, region: str, limit: int, window_h: int) -> list[TrendCandidate]:
        region = (region or "US").upper()
        url = f"https://news.google.com/rss?hl=en-{region}&gl={region}&ceid={region}:en"
        now = datetime.now(timezone.utc)
        candidates: list[TrendCandidate] = []
        for entry in fetch_feed(url, timeout_s=self.timeout_s, client=self.client):
            recency_h = max(0.0, (now - entry["published"]).total_seconds() / 3600)
            if recency_h > window_h:
                continue
            candidates.append(
                TrendCandidate(
                    id="gn:" + hashlib.sha256((entry["url"] or entry["title"]).encode()).hexdigest()[:16],
                    title=entry["title"],
                    source="google_news_rss",
                    url=entry["url"],
                    snippet=entry["snippet"][:500],
                    metrics={"recency_h": round(recency_h, 2)},
                    fetched_at=now,
                )
            )
            if len(candidates) >= limit:
                break
        return candidates
