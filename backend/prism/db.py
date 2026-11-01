from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .domain import Job, JobStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_id       TEXT PRIMARY KEY,
  plugin       TEXT NOT NULL,
  topic        TEXT NOT NULL,
  angle_json   TEXT,
  overrides    TEXT NOT NULL DEFAULT '{}',
  status       TEXT NOT NULL,
  stage        TEXT,
  progress     REAL NOT NULL DEFAULT 0.0,
  error_json   TEXT,
  seed         INTEGER NOT NULL,
  created_at   TEXT NOT NULL,
  started_at   TEXT,
  finished_at  TEXT,
  heartbeat_at TEXT,
  recommended_plugin TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS job_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id      TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  ts          TEXT NOT NULL,
  stage       TEXT,
  progress    REAL,
  level       TEXT NOT NULL DEFAULT 'info',
  message     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_job ON job_events(job_id, id);

CREATE TABLE IF NOT EXISTS worker_state (
  id           INTEGER PRIMARY KEY CHECK (id = 1),
  heartbeat_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trend_cache (
  key         TEXT PRIMARY KEY,
  payload     TEXT NOT NULL,
  expires_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_meta (
  job_id      TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
  metadata    TEXT NOT NULL,
  manifest    TEXT NOT NULL,
  decided_at  TEXT,
  decision    TEXT
);
"""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def connect(db_path: str | Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(db_path: str | Path) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        job_id=row["job_id"],
        plugin=row["plugin"],
        topic=row["topic"],
        angle=json.loads(row["angle_json"]) if row["angle_json"] else None,
        overrides=json.loads(row["overrides"] or "{}"),
        status=JobStatus(row["status"]),
        stage=row["stage"],
        progress=row["progress"],
        error=json.loads(row["error_json"]) if row["error_json"] else None,
        created_at=parse_dt(row["created_at"]),
        started_at=parse_dt(row["started_at"]),
        finished_at=parse_dt(row["finished_at"]),
    )


def insert_job(conn: sqlite3.Connection, job: Job, seed: int, recommended_plugin: str | None = None) -> None:
    conn.execute(
        """INSERT INTO jobs (job_id, plugin, topic, angle_json, overrides, status, stage, progress,
                             error_json, seed, created_at, started_at, finished_at, heartbeat_at, recommended_plugin)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job.job_id,
            job.plugin,
            job.topic,
            json.dumps(job.angle) if job.angle is not None else None,
            json.dumps(job.overrides),
            job.status.value,
            job.stage,
            job.progress,
            json.dumps(job.error) if job.error else None,
            seed,
            iso(job.created_at),
            iso(job.started_at) if job.started_at else None,
            iso(job.finished_at) if job.finished_at else None,
            None,
            recommended_plugin,
        ),
    )
    conn.commit()


def get_job(conn: sqlite3.Connection, job_id: str) -> Job | None:
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def get_job_row(conn: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()


def list_jobs(
    conn: sqlite3.Connection, *, status: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[sqlite3.Row], int]:
    where, params = "", []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    total = conn.execute(f"SELECT COUNT(*) AS n FROM jobs {where}", params).fetchone()["n"]
    rows = conn.execute(
        f"SELECT * FROM jobs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return rows, total


def update_job(conn: sqlite3.Connection, job_id: str, **fields: Any) -> None:
    allowed = {
        "status", "stage", "progress", "error_json", "started_at", "finished_at", "heartbeat_at",
    }
    sets, params = [], []
    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"Cannot update jobs.{key}")
        sets.append(f"{key} = ?")
        params.append(value)
    if not sets:
        return
    params.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = ?", params)
    conn.commit()


def update_job_status(conn: sqlite3.Connection, job_id: str, status: JobStatus, **extra: Any) -> None:
    update_job(conn, job_id, status=status.value, **extra)


def set_job_error(conn: sqlite3.Connection, job_id: str, error: dict[str, Any]) -> None:
    update_job(conn, job_id, error_json=json.dumps(error))


def append_event(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    stage: str | None,
    progress: float | None,
    message: str,
    level: str = "info",
) -> None:
    conn.execute(
        "INSERT INTO job_events (job_id, ts, stage, progress, level, message) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, iso(now_utc()), stage, progress, level, message),
    )
    conn.commit()


def list_events(conn: sqlite3.Connection, job_id: str, since: int = 0, limit: int = 200) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM job_events WHERE job_id = ? AND id > ? ORDER BY id ASC LIMIT ?",
        (job_id, since, limit),
    ).fetchall()


def set_worker_heartbeat(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO worker_state (id, heartbeat_at) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET heartbeat_at = excluded.heartbeat_at",
        (iso(now_utc()),),
    )
    conn.commit()


def get_worker_heartbeat(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT heartbeat_at FROM worker_state WHERE id = 1").fetchone()
    return row["heartbeat_at"] if row else None


def worker_alive(conn: sqlite3.Connection, stale_s: int) -> tuple[bool, str | None]:
    last = get_worker_heartbeat(conn)
    if not last:
        return False, None
    return now_utc() - parse_dt(last) < timedelta(seconds=stale_s), last


def fail_stale_running_jobs(conn: sqlite3.Connection, stale_s: int) -> list[str]:
    cutoff = iso(now_utc() - timedelta(seconds=stale_s))
    rows = conn.execute(
        """SELECT job_id FROM jobs
           WHERE status = 'RUNNING'
             AND COALESCE(heartbeat_at, started_at, created_at) < ?""",
        (cutoff,),
    ).fetchall()
    failed: list[str] = []
    for row in rows:
        job_id = row["job_id"]
        error = {
            "error_class": "WorkerLost",
            "stage": "worker",
            "message": "Worker heartbeat went stale while this job was running.",
            "retryable": True,
            "context": {},
        }
        update_job(
            conn,
            job_id,
            status=JobStatus.FAILED.value,
            finished_at=iso(now_utc()),
            error_json=json.dumps(error),
        )
        append_event(conn, job_id, stage="worker", progress=None, level="error", message=error["message"])
        failed.append(job_id)
    return failed


def get_review_meta(conn: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM review_meta WHERE job_id = ?", (job_id,)).fetchone()


def upsert_review_meta(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    metadata: dict[str, Any],
    manifest: dict[str, Any],
    decision: str | None = None,
    decided_at: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO review_meta (job_id, metadata, manifest, decided_at, decision)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(job_id) DO UPDATE SET
             metadata = excluded.metadata,
             manifest = excluded.manifest,
             decided_at = COALESCE(excluded.decided_at, review_meta.decided_at),
             decision = COALESCE(excluded.decision, review_meta.decision)""",
        (job_id, json.dumps(metadata), json.dumps(manifest), decided_at, decision),
    )
    conn.commit()


def set_review_decision(conn: sqlite3.Connection, job_id: str, decision: str) -> None:
    conn.execute(
        "UPDATE review_meta SET decision = ?, decided_at = ? WHERE job_id = ?",
        (decision, iso(now_utc()), job_id),
    )
    conn.commit()


def cache_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT payload FROM trend_cache WHERE key = ? AND expires_at > ?", (key, iso(now_utc()))).fetchone()
    return row["payload"] if row else None


def cache_set(conn: sqlite3.Connection, key: str, payload: str, ttl_min: int) -> None:
    expires = iso(now_utc() + timedelta(minutes=ttl_min))
    conn.execute(
        "INSERT INTO trend_cache (key, payload, expires_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, expires_at = excluded.expires_at",
        (key, payload, expires),
    )
    conn.commit()
