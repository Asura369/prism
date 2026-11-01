from __future__ import annotations

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from ...adapters.base import TrendSourceAdapter
from ...domain import TrendCandidate

log = logging.getLogger(__name__)
TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
TAG_RE = re.compile(r"<[^>]+>")


def _clean(value: str | None) -> str:
    return html.unescape(TAG_RE.sub(" ", value or "")).strip()


class HackerNewsTop(TrendSourceAdapter):
    name = "hackernews"

    def __init__(self, timeout_s: int = 10, client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self.client = client

    def _fetch_item(self, client: httpx.Client, item_id: int) -> dict | None:
        try:
            response = client.get(ITEM_URL.format(item_id=item_id))
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - skip individual items
            log.debug("hackernews item %s failed: %s", item_id, exc)
            return None

    def fetch(self, *, region: str, limit: int, window_h: int) -> list[TrendCandidate]:
        client = self.client or httpx.Client(timeout=self.timeout_s, headers={"User-Agent": "prism-trend-bot/0.1"})
        try:
            response = client.get(TOP_URL)
            response.raise_for_status()
            ids = list(response.json())[:limit]
            with ThreadPoolExecutor(max_workers=8) as pool:
                items = list(pool.map(lambda item_id: self._fetch_item(client, item_id), ids))
            now = datetime.now(timezone.utc)
            candidates: list[TrendCandidate] = []
            for item in items:
                if not item or item.get("type") != "story" or item.get("deleted") or item.get("dead"):
                    continue
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                published_at = datetime.fromtimestamp(item.get("time") or now.timestamp(), tz=timezone.utc)
                recency_h = max(0.0, (now - published_at).total_seconds() / 3600)
                if recency_h > window_h:
                    continue
                item_id = item.get("id")
                candidates.append(
                    TrendCandidate(
                        id=f"hn:{item_id}",
                        title=title,
                        source="hackernews",
                        url=item.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
                        snippet=_clean(item.get("text"))[:500],
                        metrics={
                            "points": float(item.get("score") or 0),
                            "descendants": float(item.get("descendants") or 0),
                            "recency_h": round(recency_h, 2),
                        },
                        fetched_at=now,
                    )
                )
            return candidates
        except Exception as exc:  # noqa: BLE001 - recorded as sources_failed by the service
            log.warning("hackernews failed: %s", exc)
            raise
        finally:
            if self.client is None:
                client.close()
