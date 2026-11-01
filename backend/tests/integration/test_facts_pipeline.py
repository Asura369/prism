from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

from PIL import Image

from prism import db
from prism.adapters.resolver import AdapterResolver
from prism.config import Config, Secrets
from prism.domain import Job, JobStatus
from prism.orchestrator import Orchestrator
from prism.plugins.registry import PluginRegistry


def _job() -> Job:
    return Job(
        job_id="job_integration01",
        plugin="facts_carousel",
        topic="Octopus facts",
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


def test_facts_pipeline_end_to_end(cfg: Config, secrets: Secrets):
    secrets.fake_adapters = True
    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)
    job = _job()
    db.insert_job(conn, job, seed=42)
    resolver = AdapterResolver(cfg, secrets)
    registry = PluginRegistry(cfg, resolver)
    artifact = Orchestrator(cfg, resolver, registry, conn, job, seed=42).run()

    assert artifact.final_sequence.exists()
    assert artifact.thumbnail.exists()
    assert artifact.metadata.exists()
    assert artifact.manifest.exists()
    assert artifact.status.exists()

    with zipfile.ZipFile(artifact.final_sequence) as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".png"))
        assert names == [f"{i:02d}.png" for i in range(1, 8)]
        for name in names:
            with Image.open(zf.open(name)) as img:
                assert img.size == (1080, 1350)

    import json

    metadata = json.loads(artifact.metadata.read_text())
    assert len(metadata["alt_text"]) == 7
    assert all(metadata["alt_text"])
    assert metadata["ai_disclosure"] is True
    assert metadata["caption"]

    manifest = json.loads(artifact.manifest.read_text())
    assert manifest["status"] == "REVIEW_READY"
    assert manifest["plugin"] == "facts_carousel"
    assert manifest["error"] is None
    assert manifest["adapters"]["llm"]["name"] == "fake"

    row = db.get_job(conn, job.job_id)
    assert row is not None
    conn.close()
