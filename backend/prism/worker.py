from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import time
from pathlib import Path

from . import db
from .adapters.resolver import AdapterResolver
from .config import load_config, resolve_path
from .domain import JobStatus
from .errors import JobCancelled
from .orchestrator import Orchestrator
from .plugins.registry import PluginRegistry

log = logging.getLogger("prism.worker")
HEARTBEAT_S = 5.0


class Worker:
    def __init__(self) -> None:
        self.cfg = load_config()
        self.db_path = resolve_path(self.cfg.run.db_path, self.cfg.base_dir)
        db.init_db(self.db_path)
        self.conn = db.connect(self.db_path)
        self.resolver = AdapterResolver(self.cfg)
        self.registry = PluginRegistry(self.cfg, self.resolver)
        self.stop = threading.Event()
        self.current_job_id: str | None = None
        self._heartbeat_thread: threading.Thread | None = None

    def _heartbeat_loop(self) -> None:
        conn = db.connect(self.db_path)
        while not self.stop.wait(HEARTBEAT_S):
            try:
                db.set_worker_heartbeat(conn)
                if self.current_job_id:
                    db.update_job(conn, self.current_job_id, heartbeat_at=db.iso(db.now_utc()))
            except Exception as exc:  # noqa: BLE001 - keep the worker alive
                log.warning("heartbeat failed: %s", exc)
        conn.close()

    def _claim(self):
        row = self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'QUEUED' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        now = db.iso(db.now_utc())
        cur = self.conn.execute(
            "UPDATE jobs SET status = 'RUNNING', started_at = ?, stage = 'spec', progress = 0.0, "
            "heartbeat_at = ? WHERE job_id = ? AND status = 'QUEUED'",
            (now, now, row["job_id"]),
        )
        self.conn.commit()
        if cur.rowcount != 1:
            return None
        db.append_event(self.conn, row["job_id"], stage="spec", progress=0.0, message="Job started")
        return db.get_job_row(self.conn, row["job_id"])

    def _finish(self, job_id: str, status: JobStatus, error: dict | None = None) -> None:
        fields = {"status": status.value, "finished_at": db.iso(db.now_utc())}
        if error is not None:
            fields["error_json"] = json.dumps(error)
        db.update_job(self.conn, job_id, **fields)
        db.append_event(
            self.conn,
            job_id,
            stage=None,
            progress=None,
            level="info" if status != JobStatus.FAILED else "error",
            message=f"Job {status.value}" + (f": {error['message']}" if error else ""),
        )

    def run_once(self, row) -> None:
        job = db.get_job(self.conn, row["job_id"])
        if job is None:
            return
        self.current_job_id = job.job_id
        recommended = row["recommended_plugin"]
        try:
            orchestrator = Orchestrator(
                self.cfg, self.resolver, self.registry, self.conn, job, row["seed"], recommended
            )
            orchestrator.run()
            self._finish(job.job_id, JobStatus.REVIEW_READY)
            log.info("job %s -> REVIEW_READY", job.job_id)
        except JobCancelled:
            self._finish(job.job_id, JobStatus.CANCELLED)
            log.info("job %s cancelled", job.job_id)
        except Exception as exc:  # noqa: BLE001 - job boundary
            error = (
                exc.to_dict()
                if hasattr(exc, "to_dict")
                else {
                    "error_class": exc.__class__.__name__,
                    "stage": getattr(job, "stage", None),
                    "message": str(exc),
                    "retryable": False,
                    "context": {},
                }
            )
            self._finish(job.job_id, JobStatus.FAILED, error)
            log.error("job %s FAILED at %s: %s", job.job_id, error.get("stage"), error.get("message"))
        finally:
            self.current_job_id = None

    def run_forever(self) -> None:
        db.set_worker_heartbeat(self.conn)
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        log.info("worker started; polling for QUEUED jobs")
        while not self.stop.is_set():
            row = self._claim()
            if row is None:
                self.stop.wait(1.0)
                continue
            self.run_once(row)
        db.set_worker_heartbeat(self.conn)
        self.conn.close()
        log.info("worker stopped")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    worker = Worker()

    def _shutdown(signum, frame):  # noqa: ANN001
        log.info("signal %s received; stopping after current step", signum)
        worker.stop.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    worker.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
