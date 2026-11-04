from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

USER_AGENT = "prism-bot/0.1"
TAG_RE = re.compile(r"<[^>]+>")


def _clean(value: str | None) -> str:
    return html.unescape(TAG_RE.sub(" ", value or "")).strip()


def fetch_feed(url: str, *, timeout_s: int = 10, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Fetch an RSS feed as [{title, url, snippet, source, published}] entries."""
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout_s, headers={"User-Agent": USER_AGENT})
    try:
        response = client.get(url)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        now = datetime.now(timezone.utc)
        entries: list[dict[str, Any]] = []
        for entry in feed.entries:
            title = _clean(entry.get("title"))
            if not title:
                continue
            published = entry.get("published_parsed")
            entries.append(
                {
                    "title": title,
                    "url": entry.get("link", ""),
                    "snippet": _clean(entry.get("summary")),
                    "source": _clean((entry.get("source") or {}).get("title")),
                    "published": datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
                    if published
                    else now,
                }
            )
        return entries
    finally:
        if owns_client:
            client.close()
