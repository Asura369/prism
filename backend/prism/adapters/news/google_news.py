from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus, urlparse

import feedparser
import httpx

from ..base import NewsSourceAdapter

USER_AGENT = "prism-news-bot/0.1"
REGION = "US"
TAG_RE = re.compile(r"<[^>]+>")
QUERY_URL = "https://news.google.com/rss/search?q={query}&hl={lang}-{region}&gl={region}&ceid={region}:{lang}"


def _clean(value: str | None) -> str:
    return html.unescape(TAG_RE.sub(" ", value or "")).strip()


class GoogleNewsRSSNews(NewsSourceAdapter):
    name = "google_news_rss"

    def __init__(self, timeout_s: int = 10, client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self.client = client

    def fetch_articles(
        self, *, query: str, max_articles: int, language: str = "en"
    ) -> list[dict[str, Any]]:
        lang = language.split("-")[0]
        url = QUERY_URL.format(query=quote_plus(query), lang=lang, region=REGION)
        client = self.client or httpx.Client(timeout=self.timeout_s, headers={"User-Agent": USER_AGENT})
        try:
            response = client.get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            now = datetime.now(timezone.utc)
            articles: list[dict[str, Any]] = []
            for entry in feed.entries:
                title = _clean(entry.get("title"))
                if not title:
                    continue
                link = entry.get("link", "")
                published = entry.get("published_parsed")
                if published:
                    published_at = datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
                else:
                    published_at = now
                source_name = _clean(entry.get("source", {}).get("title")) or urlparse(
                    link
                ).netloc.removeprefix("www.")
                articles.append(
                    {
                        "title": title,
                        "url": link,
                        "snippet": _clean(entry.get("summary")),
                        "published_at": published_at.isoformat(),
                        "source_name": source_name,
                    }
                )
                if len(articles) >= max_articles:
                    break
            return articles
        finally:
            if self.client is None:
                client.close()
