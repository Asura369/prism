from __future__ import annotations

import httpx

from prism.adapters.news.fake import FakeNews
from prism.adapters.news.google_news import GoogleNewsRSSNews
from prism.adapters.resolver import AdapterResolver
from prism.config import Config, Secrets

RSS_XML = """<?xml version="1.0"?><rss version="2.0"><channel>
<item>
  <title>Seabed mining talks resume</title>
  <link>https://news.google.com/rss/articles/AAA?oc=5</link>
  <pubDate>Wed, 01 Nov 2026 00:00:00 GMT</pubDate>
  <description>&lt;a href="https://example.news/mining"&gt;Regulators&lt;/a&gt; resumed talks on deep sea mining.</description>
  <source url="https://www.reuters.com">Reuters</source>
</item>
<item>
  <title>Nodule study published</title>
  <link>https://news.google.com/rss/articles/BBB?oc=5</link>
  <pubDate>Tue, 31 Oct 2026 00:00:00 GMT</pubDate>
  <description>&lt;b&gt;Researchers&lt;/b&gt; mapped nodule fields in the Clarion-Clipperton Zone.</description>
</item>
</channel></rss>"""


def test_fake_news_is_deterministic_with_one_duplicate_url():
    first = FakeNews().fetch_articles(query="deep sea mining", max_articles=5)
    assert first == FakeNews().fetch_articles(query="deep sea mining", max_articles=5)
    assert len(first) == 4
    assert len({a["url"] for a in first}) == 3
    assert all(set(a) == {"title", "url", "snippet", "published_at", "source_name"} for a in first)


def test_fake_news_respects_max_articles():
    assert len(FakeNews().fetch_articles(query="x", max_articles=2)) == 2


def test_google_news_news_parses_rss():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=RSS_XML))
    adapter = GoogleNewsRSSNews(client=httpx.Client(transport=transport))
    articles = adapter.fetch_articles(query="deep sea mining", max_articles=5)
    assert articles[0]["title"] == "Seabed mining talks resume"
    assert articles[0]["url"].startswith("https://news.google.com/")
    assert articles[0]["source_name"] == "Reuters"
    assert "<" not in articles[0]["snippet"]
    assert articles[1]["source_name"] == "news.google.com"


def test_news_chain_real(cfg: Config, secrets: Secrets):
    assert AdapterResolver(cfg, secrets).chain_names("news") == ["google_news_rss"]


def test_news_chain_fake(cfg: Config, secrets: Secrets):
    secrets.fake_adapters = True
    assert AdapterResolver(cfg, secrets).chain_names("news") == ["fake"]
