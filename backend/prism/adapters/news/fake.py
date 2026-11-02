from __future__ import annotations

from typing import Any

from ..base import NewsSourceAdapter

ARTICLES: list[dict[str, Any]] = [
    {
        "title": "Seabed mining talks resume in Kingston",
        "url": "https://example.news/mining",
        "snippet": "Delegates are meeting again to discuss rules for extracting metals from the deep seabed.",
        "published_at": "2026-11-01T00:00:00+00:00",
        "source_name": "Reuters",
    },
    {
        "title": "Scientists map nodule fields",
        "url": "https://example.news/nodules",
        "snippet": "Researchers mapped nodule fields in the Clarion-Clipperton Zone, where ecosystems recover slowly.",
        "published_at": "2026-10-31T00:00:00+00:00",
        "source_name": "Nature",
    },
    {
        "title": "Coral reefs face a hotter decade",
        "url": "https://example.news/reef",
        "snippet": "Reef surveys show bleaching is becoming more frequent as ocean temperatures climb.",
        "published_at": "2026-10-30T00:00:00+00:00",
        "source_name": "ScienceDaily",
    },
    {
        "title": "Reef recovery is slower than expected",
        "url": "https://example.news/reef",
        "snippet": "A follow-up study finds that coral recovery lags behind the pace of repeated heat waves.",
        "published_at": "2026-10-29T00:00:00+00:00",
        "source_name": "ScienceDaily",
    },
]


class FakeNews(NewsSourceAdapter):
    name = "fake"

    def fetch_articles(self, *, query: str, max_articles: int, language: str = "en") -> list[dict[str, Any]]:
        return [dict(article) for article in ARTICLES[:max_articles]]
