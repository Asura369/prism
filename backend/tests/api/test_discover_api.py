from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from prism.config import Config, Secrets
from prism.discovery import service
from prism.domain import TrendCandidate
from prism.main import create_app


def _client(cfg: Config) -> TestClient:
    secrets = Secrets(
        llm_key="",
        fake_adapters=True,
        prism_config="",
        prism_db_path="",
        _env_file=None,
    )
    return TestClient(create_app(cfg, secrets))


def _candidate() -> TrendCandidate:
    return TrendCandidate(
        id="gn:test1",
        title="Why the ocean is still mostly unexplored",
        source="google_news_rss",
        url="https://example.com/ocean",
        snippet="Most of the sea floor has never been mapped at high resolution.",
        metrics={"recency_h": 2.0},
        fetched_at=datetime.now(timezone.utc),
    )


class FakeSource:
    name = "google_news_rss"

    def fetch(self, *, region, limit, window_h):
        return [_candidate()]


def test_trends_endpoint_returns_scored_candidates(cfg: Config, monkeypatch):
    monkeypatch.setattr(service, "build_sources", lambda cfg: {"google_news_rss": FakeSource()})
    with _client(cfg) as client:
        response = client.get("/api/discover/trends?region=US&window_h=24")
        assert response.status_code == 200
        body = response.json()
        assert body["sources_used"] == ["google_news_rss"]
        assert body["candidates"][0]["candidate"]["id"] == "gn:test1"
        assert "combined" in body["candidates"][0]["score"]


def test_source_failure_is_reported(cfg: Config, monkeypatch):
    class Broken:
        name = "google_news_rss"

        def fetch(self, **_):
            raise RuntimeError("nope")

    class Good:
        name = "hackernews"

        def fetch(self, **_):
            item = _candidate()
            item.source = "hackernews"
            item.id = "hn:good"
            return [item]

    monkeypatch.setattr(service, "build_sources", lambda cfg: {"google_news_rss": Broken(), "hackernews": Good()})
    with _client(cfg) as client:
        body = client.get("/api/discover/trends").json()
        assert body["sources_failed"] == ["google_news_rss"]
        assert body["sources_used"] == ["hackernews"]
        assert body["candidates"][0]["candidate"]["id"] == "hn:good"


def test_manual_angles_and_select_flow(cfg: Config):
    with _client(cfg) as client:
        manual = client.post(
            "/api/discover/manual",
            json={"title": "Why the ocean is still mostly unexplored", "snippet": "A short context"},
        )
        assert manual.status_code == 200
        manual_body = manual.json()
        candidate_id = manual_body["candidate_id"]

        angles = client.post("/api/discover/angles", json={"candidate_id": candidate_id})
        assert angles.status_code == 200
        angle_body = angles.json()["angles"]
        assert len(angle_body) == 3
        assert all(angle["recommended_plugin"] == "facts_carousel" for angle in angle_body)
        assert angle_body[1]["plugin_reasoning"].startswith("auto-routed")
        assert angle_body[2]["plugin_reasoning"].startswith("auto-routed")
        assert angles.json()["candidate"]["candidate"]["title"] == "Why the ocean is still mostly unexplored"

        selected = client.post(
            "/api/discover/select",
            json={"candidate_id": candidate_id, "angle_index": 0, "plugin": "facts_carousel"},
        )
        assert selected.status_code == 200
        draft = selected.json()["draft_job_payload"]
        assert draft["plugin"] == "facts_carousel"
        assert draft["angle"]["hook"]
        assert draft["recommended_plugin"] == "facts_carousel"


def test_angles_on_unknown_candidate_returns_409(cfg: Config):
    with _client(cfg) as client:
        response = client.post("/api/discover/angles", json={"candidate_id": "nope"})
        assert response.status_code == 409
        assert response.json()["error"] == "trend_expired"


def test_csv_upload_and_invalid_csv(cfg: Config):
    with _client(cfg) as client:
        content = b"Query,Score\noctopus facts,Breakout\nweird ocean,<1%\n"
        response = client.post(
            "/api/discover/trends/upload",
            files={"file": ("trends.csv", content, "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["imported_count"] == 2
        assert len(response.json()["candidates"]) == 2

        bad = client.post(
            "/api/discover/trends/upload",
            files={"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")},
        )
        assert bad.status_code == 400
        assert bad.json()["error"] == "invalid_trends_csv"
        assert "Expected columns" in bad.json()["message"]
