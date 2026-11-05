from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from prism import db
from prism.adapters.llm.stub import NEWS_SETS, StubLLM
from prism.adapters.news.stub import StubNews
from prism.adapters.resolver import AdapterResolver
from prism.config import Config, Secrets
from prism.domain import Job, JobStatus
from prism.errors import InsufficientSourcesError, PolicyViolation
from prism.orchestrator import Orchestrator
from prism.plugins.registry import PluginRegistry


def _news_job() -> Job:
    return Job(
        job_id="job_news01",
        plugin="news_carousel",
        topic="Deep sea mining",
        angle=None,
        overrides={},
        status=JobStatus.QUEUED,
        stage=None,
        progress=0.0,
        error=None,
        created_at=db.now_utc(),
        started_at=None,
        finished_at=None,
    )


def test_news_pipeline_end_to_end(cfg: Config, secrets: Secrets):
    secrets.stub_adapters = True
    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)
    job = _news_job()
    db.insert_job(conn, job, seed=7)
    resolver = AdapterResolver(cfg, secrets)
    registry = PluginRegistry(cfg, resolver)
    orch = Orchestrator(cfg, resolver, registry, conn, job, seed=7)
    artifact = orch.run()

    kinds = [s.kind for s in orch.spec.slides]
    assert kinds.count("sources") == 1 and kinds[0] == "cover" and kinds[-1] == "cta"
    assert all(0 <= s.meta["source_index"] < len(orch.spec.sources) for s in orch.spec.slides if s.kind == "news_point")

    manifest = json.loads(artifact.manifest.read_text())
    assert manifest["ingest"]["adapter"] == "news"
    assert manifest["ingest"]["failed_adapters"] == []
    assert manifest["ingest"]["params"] == orch.plugin.ingest_config["params"]
    assert len(manifest["ingest"]["sources"]) == 4  # 4 fetched, all unique URLs
    assert manifest["sources"] == manifest["ingest"]["sources"] == orch.spec.sources

    metadata = json.loads(artifact.metadata.read_text())
    assert all(src["name"] in metadata["caption"] for src in orch.spec.sources)
    assert len(metadata["alt_text"]) == len(kinds)
    assert all(metadata["alt_text"])

    with zipfile.ZipFile(artifact.final_sequence) as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".png"))
        assert names == [f"{i:02d}.png" for i in range(1, len(kinds) + 1)]
        for name in names:
            with Image.open(zf.open(name)) as img:
                assert img.size == (1080, 1350)


class _OneArticleNews(StubNews):
    def fetch_articles(self, *, query, max_articles, language="en"):
        return super().fetch_articles(query=query, max_articles=1)


class _FailingNews(StubNews):
    def fetch_articles(self, *, query, max_articles, language="en"):
        raise RuntimeError("news feed unreachable")


class _BlockedLLM(StubLLM):
    def complete(self, prompt, **kwargs):
        if '"news_points"' in prompt:
            payload = json.loads(json.dumps(NEWS_SETS[0]))
            payload["title"] = "Politics of the seabed"
            return json.dumps(payload)
        return super().complete(prompt, **kwargs)


def _orchestrator(cfg, secrets, job):
    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)
    db.insert_job(conn, job, seed=7)
    resolver = AdapterResolver(cfg, secrets)
    registry = PluginRegistry(cfg, resolver)
    return Orchestrator(cfg, resolver, registry, conn, job, seed=7)


def _failure_manifest(cfg: Config, job: Job) -> dict:
    path = Path(cfg.run.work_dir) / job.job_id / "manifest.json"
    return json.loads(path.read_text())


def test_insufficient_sources_fails_the_job(cfg, secrets):
    secrets.stub_adapters = True
    job = _news_job()
    orch = _orchestrator(cfg, secrets, job)
    orch.resolver._registry["news"]["stub"] = _OneArticleNews()
    with pytest.raises(InsufficientSourcesError) as exc:
        orch.run()
    assert (exc.value.context["found"], exc.value.context["required"]) == (1, 2)

    failed = _failure_manifest(cfg, job)
    assert failed["status"] == "FAILED"
    assert failed["error"]["error_class"] == "InsufficientSourcesError"
    assert "ingest" not in failed


def test_news_adapter_failure_is_recorded_in_the_manifest(cfg, secrets):
    secrets.stub_adapters = True
    job = _news_job()
    orch = _orchestrator(cfg, secrets, job)
    orch.resolver._registry["news"]["stub"] = _FailingNews()
    with pytest.raises(InsufficientSourcesError) as exc:
        orch.run()
    assert exc.value.context["found"] == 0

    failed = _failure_manifest(cfg, job)
    assert failed["status"] == "FAILED"
    assert "ingest" not in failed
    assert isinstance(failed["ingest_errors"], list) and failed["ingest_errors"]
    assert failed["ingest_errors"][0]["adapter"] == "stub"
    assert failed["ingest_errors"][0]["error"]


def test_blocked_topic_fails_policy(cfg, secrets):
    secrets.stub_adapters = True
    job = _news_job()
    orch = _orchestrator(cfg, secrets, job)
    orch.resolver._registry["llm"]["stub"] = _BlockedLLM()
    with pytest.raises(PolicyViolation):
        orch.run()
    failed = _failure_manifest(cfg, job)
    assert failed["status"] == "FAILED"
    assert failed["error"]["error_class"] == "PolicyViolation"
