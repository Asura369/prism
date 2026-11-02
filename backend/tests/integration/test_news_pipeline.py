from __future__ import annotations

import json
import zipfile

from PIL import Image

from prism import db
from prism.adapters.resolver import AdapterResolver
from prism.config import Config, Secrets
from prism.domain import Job, JobStatus
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
    secrets.fake_adapters = True
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
    assert len(manifest["ingest"]["sources"]) == 3  # 4 fetched, 1 duplicate URL
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
