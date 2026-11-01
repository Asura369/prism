from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from prism import db
from prism.config import Config, Secrets
from prism.domain import Job, JobStatus
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


def test_plugins_endpoint(cfg: Config):
    with _client(cfg) as client:
        response = client.get("/api/plugins")
        assert response.status_code == 200
        plugins = response.json()
        facts = next(p for p in plugins if p["name"] == "facts_carousel")
        assert facts["available"] is True
        assert facts["output_kind"] == "image_sequence"


def test_health_without_worker(cfg: Config):
    with _client(cfg) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["worker"]["alive"] is False
        assert body["worker"]["last_heartbeat"] is None


def test_create_and_list_job(cfg: Config):
    with _client(cfg) as client:
        response = client.post("/api/jobs", json={"plugin": "facts_carousel", "topic": "Octopus facts"})
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        listed = client.get("/api/jobs").json()
        assert listed["total"] == 1
        assert listed["items"][0]["status"] == "QUEUED"

        detail = client.get(f"/api/jobs/{job_id}").json()
        assert detail["job"]["topic"] == "Octopus facts"
        assert [s["name"] for s in detail["stages"]][0] == "spec"
        assert detail["events_tail"]


def test_unknown_plugin_rejected(cfg: Config):
    with _client(cfg) as client:
        response = client.post("/api/jobs", json={"plugin": "nope", "topic": "x"})
        assert response.status_code == 404
        assert response.json()["error"] == "plugin_not_found"


def test_cancel_queued_job(cfg: Config):
    with _client(cfg) as client:
        job_id = client.post("/api/jobs", json={"plugin": "facts_carousel", "topic": "x"}).json()["job_id"]
        assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 200
        assert client.get(f"/api/jobs/{job_id}").json()["job"]["status"] == "CANCELLED"
        assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 409


def test_stale_running_job_marked_worker_lost(cfg: Config):
    client = _client(cfg)
    with client:
        conn = db.connect(cfg.run.db_path)
        stale = db.iso(db.now_utc() - timedelta(seconds=60))
        job = Job(
            job_id="job_stale",
            plugin="facts_carousel",
            topic="stale",
            angle=None,
            overrides={},
            status=JobStatus.RUNNING,
            stage="render",
            progress=0.4,
            error=None,
            created_at=db.now_utc(),
            started_at=db.now_utc(),
            finished_at=None,
        )
        db.insert_job(conn, job, seed=1)
        db.update_job(conn, job.job_id, status="RUNNING", stage="render", heartbeat_at=stale)
        conn.close()

        detail = client.get("/api/jobs/job_stale").json()
        assert detail["job"]["status"] == "FAILED"
        assert detail["job"]["error"]["error_class"] == "WorkerLost"


def test_settings_exposes_deepseek_key_only(cfg: Config):
    with _client(cfg) as client:
        body = client.get("/api/settings").json()
        assert set(body["keys"]) == {"LLM_KEY"}
        assert [item["name"] for item in body["adapters"]["llm"]] == ["fake"]
