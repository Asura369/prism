from __future__ import annotations

import io
import json
import zipfile

from fastapi.testclient import TestClient

from prism import db
from prism.config import Config, Secrets
from prism.domain import JobStatus
from prism.main import create_app
from prism.orchestrator import Orchestrator


def _app_client(cfg: Config):
    secrets = Secrets(
        llm_key="",
        fake_adapters=True,
        prism_config="",
        prism_db_path="",
        _env_file=None,
    )
    app = create_app(cfg, secrets)
    return app, TestClient(app)


def _completed_job(cfg: Config, client: TestClient):
    job_id = client.post("/api/jobs", json={"plugin": "facts_carousel", "topic": "Review me"}).json()["job_id"]
    conn = db.connect(cfg.run.db_path)
    row = db.get_job_row(conn, job_id)
    job = db.get_job(conn, job_id)
    Orchestrator(cfg, client.app.state.resolver, client.app.state.registry, conn, job, row["seed"]).run()
    db.update_job_status(conn, job_id, JobStatus.REVIEW_READY, finished_at=db.iso(db.now_utc()))
    conn.close()
    return job_id


def test_review_queue_and_detail(cfg: Config):
    _, client = _app_client(cfg)
    job_id = _completed_job(cfg, client)

    queue = client.get("/api/review").json()
    assert [item["job_id"] for item in queue] == [job_id]
    assert queue[0]["decision"] is None

    detail = client.get(f"/api/review/{job_id}").json()
    assert detail["metadata"]["ai_disclosure"] is True
    assert len(detail["artifact_urls"]["slides"]) == 7
    assert detail["artifact_urls"]["download"].endswith("/download")


def test_patch_metadata_writes_disk_then_db(cfg: Config):
    _, client = _app_client(cfg)
    job_id = _completed_job(cfg, client)

    response = client.patch(
        f"/api/review/{job_id}/metadata",
        json={"caption": "Edited caption", "hashtags": ["#one", "two"], "title": "Edited title"},
    )
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["caption"] == "Edited caption"
    assert metadata["hashtags"] == ["one", "two"]

    on_disk = json.loads((cfg.base_dir / cfg.run.output_dir / job_id / "metadata.json").read_text())
    assert on_disk["caption"] == "Edited caption"
    assert on_disk["title"] == "Edited title"
    row = db.connect(cfg.run.db_path).execute(
        "SELECT metadata FROM review_meta WHERE job_id = ?", (job_id,)
    ).fetchone()
    assert json.loads(row["metadata"])["caption"] == "Edited caption"


def test_alt_text_count_is_validated(cfg: Config):
    _, client = _app_client(cfg)
    job_id = _completed_job(cfg, client)
    response = client.patch(f"/api/review/{job_id}/metadata", json={"alt_text": ["only one"]})
    assert response.status_code == 400
    assert response.json()["error"] == "alt_text_count_mismatch"


def test_approve_moves_job_out_of_queue(cfg: Config):
    _, client = _app_client(cfg)
    job_id = _completed_job(cfg, client)

    assert client.post(f"/api/review/{job_id}/approve").status_code == 200
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["job"]["status"] == "APPROVED"
    assert client.get(f"/api/review/{job_id}").json()["metadata"]["ai_disclosure"] is True
    assert client.post(f"/api/review/{job_id}/approve").status_code == 409

    queue = client.get("/api/review").json()
    assert all(item["job_id"] != job_id for item in queue)


def test_reject_requires_reason(cfg: Config):
    _, client = _app_client(cfg)
    job_id = _completed_job(cfg, client)
    assert client.post(f"/api/review/{job_id}/reject", json={"reason": ""}).status_code == 422
    assert client.post(f"/api/review/{job_id}/reject", json={"reason": "off-topic"}).status_code == 200
    assert client.get(f"/api/jobs/{job_id}").json()["job"]["status"] == "REJECTED"


def test_download_is_a_flat_zip(cfg: Config):
    _, client = _app_client(cfg)
    job_id = _completed_job(cfg, client)
    response = client.get(f"/api/review/{job_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = set(zf.namelist())
    assert {f"slides/{i:02d}.png" for i in range(1, 8)} <= names
    assert {"caption.txt", "metadata.json", "manifest.json", "status.json"} <= names
