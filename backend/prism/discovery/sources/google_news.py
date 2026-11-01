from __future__ import annotations

import calendar
import hashlib
import html
import logging
import re
from datetime import datetime, timezone

import feedparser
import httpx

from ...adapters.base import TrendSourceAdapter
from ...domain import TrendCandidate

log = logging.getLogger(__name__)
USER_AGENT = "prism-trend-bot/0.1"
TAG_RE = re.compile(r"<[^>]+>")


def _clean(value: str | None) -> str:
    return html.unescape(TAG_RE.sub(" ", value or "")).strip()


class GoogleNewsRSS(TrendSourceAdapter):
    name = "google_news_rss"

    def __init__(self, timeout_s: int = 10, client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self.client = client

    def fetch(self, *, region: str, limit: int, window_h: int) -> list[TrendCandidate]:
        region = (region or "US").upper()
        url = f"https://news.google.com/rss?hl=en-{region}&gl={region}&ceid={region}:en"
        client = self.client or httpx.Client(timeout=self.timeout_s, headers={"User-Agent": USER_AGENT})
        try:
            response = client.get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            now = datetime.now(timezone.utc)
            candidates: list[TrendCandidate] = []
            for entry in feed.entries:
                published = entry.get("published_parsed")
                if published:
                    published_at = datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
                else:
                    published_at = now
                recency_h = max(0.0, (now - published_at).total_seconds() / 3600)
                if recency_h > window_h:
                    continue
                title = _clean(entry.get("title"))
                link = entry.get("link", "")
                if not title:
                    continue
                candidates.append(
                    TrendCandidate(
                        id="gn:" + hashlib.sha256((link or title).encode()).hexdigest()[:16],
                        title=title,
                        source="google_news_rss",
                        url=link,
                        snippet=_clean(entry.get("summary"))[:500],
                        metrics={"recency_h": round(recency_h, 2)},
                        fetched_at=now,
                    )
                )
                if len(candidates) >= limit:
                    break
            return candidates
        except Exception as exc:  # noqa: BLE001 - recorded as sources_failed by the service
            log.warning("google_news_rss failed: %s", exc)
            raise
        finally:
            if self.client is None:
                client.close()
