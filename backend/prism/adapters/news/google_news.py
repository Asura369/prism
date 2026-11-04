from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus, urlparse

from ..base import NewsSourceAdapter
from ...rss import fetch_feed

REGION = "US"
QUERY_URL = "https://news.google.com/rss/search?q={query}&hl={lang}-{region}&gl={region}&ceid={region}:{lang}"


class GoogleNewsRSSNews(NewsSourceAdapter):
    name = "google_news_rss"

    def __init__(self, timeout_s: int = 10, client=None):
        self.timeout_s = timeout_s
        self.client = client

    def fetch_articles(
        self, *, query: str, max_articles: int, language: str = "en"
    ) -> list[dict[str, Any]]:
        lang = language.split("-")[0]
        url = QUERY_URL.format(query=quote_plus(query), lang=lang, region=REGION)
        articles: list[dict[str, Any]] = []
        for entry in fetch_feed(url, timeout_s=self.timeout_s, client=self.client):
            source_name = entry["source"] or urlparse(entry["url"]).netloc.removeprefix("www.")
            articles.append(
                {
                    "title": entry["title"],
                    "url": entry["url"],
                    "snippet": entry["snippet"],
                    "published_at": entry["published"].isoformat(),
                    "source_name": source_name,
                }
            )
            if len(articles) >= max_articles:
                break
        return articles
