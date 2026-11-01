from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from prism import db
from prism.config import Config, Secrets
from prism.discovery import service
from prism.discovery.angles import default_plugin_for
from prism.discovery.cluster import cluster
from prism.discovery.score import combine, score_candidates, heuristic_score
from prism.discovery.sources.csv_upload import parse_trends_csv
from prism.discovery.sources.google_news import GoogleNewsRSS
from prism.discovery.sources.hackernews import HackerNewsTop
from prism.domain import TrendCandidate
from prism.errors import InvalidTrendsCSV
from prism.plugins.registry import PluginInfo

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _candidate(cid: str, title: str, source: str = "hackernews", recency: float = 2.0) -> TrendCandidate:
    return TrendCandidate(
        id=cid,
        title=title,
        source=source,
        url=f"https://example.com/{cid}",
        snippet="A snippet",
        metrics={"recency_h": recency, "points": 100.0, "descendants": 20.0},
        fetched_at=datetime.now(timezone.utc),
    )


def test_csv_parser_handles_bom_breakout_and_under_one_percent():
    content = (FIXTURES / "trends_related_queries.csv").read_bytes()
    candidates = parse_trends_csv(content, "trends.csv")
    assert [c.title for c in candidates] == ["octopus facts", "deep sea mining", "weird ocean"]
    assert candidates[0].metrics["score"] == 1.0
    assert candidates[2].metrics["score"] == 0.01
    assert candidates[0].metrics["filename"] == "trends.csv"
    assert len(candidates[0].metrics["sha256"]) == 64


def test_csv_parser_rejects_missing_columns():
    with pytest.raises(InvalidTrendsCSV, match="Expected columns: query \\+ score"):
        parse_trends_csv(b"foo,bar\n1,2\n", "bad.csv")


def test_csv_parser_is_case_insensitive():
    candidates = parse_trends_csv(b"TOPIC,SEARCH VOLUME\none,10\n", "x.csv")
    assert candidates[0].title == "one"


def test_clustering_keeps_one_representative():
    candidates = [
        _candidate("a", "Octopuses have three hearts"),
        _candidate("b", "Octopuses have three hearts!"),
        _candidate("c", "Octopuses have three hearts"),
        _candidate("d", "Why Iceland runs on steam"),
    ]
    reps = cluster(candidates, 0.8, {"hackernews": 0.9})
    assert len(reps) == 2
    octopus = next(rep for rep in reps if "Octopus" in rep.title)
    assert octopus.metrics["cluster_size"] == 3
    assert octopus.cluster_id.startswith("c:")
    assert len(octopus.metrics["cluster_members"]) == 3


def test_scoring_is_normalized_and_hard_filters_unsafe(cfg: Config):
    candidate = _candidate("a", "Safe topic", "hackernews")
    assert 0 <= heuristic_score(candidate, cfg) <= 1
    assert 0 <= combine(candidate, safety=0.9, visual=0.8, angle=0.8, saturation=0.2, cfg=cfg) <= 1

    class LowSafetyLLM:
        name = "fake"

        def complete(self, prompt: str, **_):
            ids = [part.split("\n")[0] for part in prompt.split("candidate_id=")[1:]]
            scores = []
            for raw in ids:
                cid = raw.split()[0]
                scores.append(
                    {
                        "id": cid,
                        "safety": 0.1 if cid == "b" else 0.9,
                        "visual_potential": 0.8,
                        "angle_ability": 0.8,
                        "saturation": 0.2,
                        "reasoning": "test",
                    }
                )
            return json.dumps({"scores": scores})

    class Resolver:
        def __init__(self):
            self.llm = LowSafetyLLM()

        def resolve(self, interface):
            return [self.llm] if interface == "llm" else []

        def require(self, interface):
            return [self.llm]

    safe = _candidate("a", "Safe topic")
    unsafe = _candidate("b", "Unsafe topic")
    scored = score_candidates(cfg, Resolver(), [safe, unsafe])  # type: ignore[arg-type]
    assert [item.candidate.id for item in scored] == ["a"]


def test_google_news_source_parses_rss():
    rss = b"""<?xml version="1.0"?><rss version="2.0"><channel><item>
    <title>Octopus story</title><link>https://example.com/octopus</link>
    <pubDate>Wed, 01 Nov 2026 00:00:00 GMT</pubDate><description>Short summary</description>
    </item></channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=rss)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    candidates = GoogleNewsRSS(client=client).fetch(region="US", limit=5, window_h=100000)
    assert len(candidates) == 1
    assert candidates[0].source == "google_news_rss"
    assert candidates[0].url == "https://example.com/octopus"


def test_hackernews_source_fetches_items():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("topstories.json"):
            return httpx.Response(200, json=[1])
        return httpx.Response(
            200,
            json={
                "id": 1,
                "type": "story",
                "title": "HN story",
                "url": "https://example.com/hn",
                "time": 1793000000,
                "score": 100,
                "descendants": 20,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    candidates = HackerNewsTop(client=client).fetch(region="US", limit=1, window_h=100000)
    assert len(candidates) == 1
    assert candidates[0].id == "hn:1"
    assert candidates[0].metrics["points"] == 100


def test_trends_cache_avoids_second_network_call(cfg: Config, monkeypatch):
    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)
    calls = {"n": 0}

    class FakeSource:
        name = "google_news_rss"

        def fetch(self, *, region, limit, window_h):
            calls["n"] += 1
            return [_candidate("gn:1", "Cached topic", "google_news_rss", 1.0)]

    monkeypatch.setattr(service, "build_sources", lambda cfg: {"google_news_rss": FakeSource()})
    secrets = Secrets(fake_adapters=True, _env_file=None)
    from prism.adapters.resolver import AdapterResolver

    resolver = AdapterResolver(cfg, secrets)
    first = service.fetch_trends(cfg, conn, resolver, region="US", window_h=24)
    second = service.fetch_trends(cfg, conn, resolver, region="US", window_h=24)
    assert calls["n"] == 1
    assert first["candidates"][0]["candidate"]["id"] == "gn:1"
    assert second["sources_used"] == ["google_news_rss"]


def test_source_failure_is_isolated(cfg: Config, monkeypatch):
    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)

    class BrokenSource:
        name = "google_news_rss"

        def fetch(self, **_):
            raise RuntimeError("network down")

    monkeypatch.setattr(service, "build_sources", lambda cfg: {"google_news_rss": BrokenSource()})
    secrets = Secrets(fake_adapters=True, _env_file=None)
    from prism.adapters.resolver import AdapterResolver

    result = service.fetch_trends(cfg, conn, AdapterResolver(cfg, secrets), region="US", window_h=24)
    assert result["sources_failed"] == ["google_news_rss"]
    assert result["candidates"] == []


def test_default_plugin_routing_prefers_news_then_qa_then_facts(cfg: Config):
    candidate = _candidate("gn:1", "Fresh news", "google_news_rss", 1.0)
    news = PluginInfo(
        name="news_carousel",
        version="0.1.0",
        description="News",
        output_kind="image_sequence",
        defaults={},
        manifest={"discovery": {"preferred_sources": ["google_news_rss"], "freshness_window_h": 48}},
        available=True,
    )
    faq = PluginInfo(
        name="faq_carousel",
        version="0.1.0",
        description="FAQ",
        output_kind="image_sequence",
        defaults={},
        manifest={},
        available=True,
    )
    facts = PluginInfo(
        name="facts_carousel",
        version="0.1.0",
        description="Facts",
        output_kind="image_sequence",
        defaults={},
        manifest={},
        available=True,
    )
    assert default_plugin_for(candidate, [news, facts]) == "news_carousel"
    assert default_plugin_for(candidate, [faq, facts], format_suggestion="qa") == "faq_carousel"
    assert default_plugin_for(candidate, [facts]) == "facts_carousel"
