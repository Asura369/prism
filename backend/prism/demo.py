from __future__ import annotations

import uuid

from . import db
from .adapters.resolver import AdapterResolver
from .config import Secrets, load_config, resolve_path
from .domain import Job, JobStatus
from .orchestrator import Orchestrator
from .plugins.registry import PluginRegistry


def main() -> int:
    cfg = load_config()
    secrets = Secrets(fake_adapters=True, _env_file=None)
    db_path = resolve_path(cfg.run.db_path, cfg.base_dir)
    db.init_db(db_path)
    conn = db.connect(db_path)
    resolver = AdapterResolver(cfg, secrets)
    registry = PluginRegistry(cfg, resolver)
    plugins = sorted(registry.names())
    if not plugins:
        print("No plugins installed.")
        return 1
    print(f"Running demo for {len(plugins)} plugin(s) with FakeLLM…")
    for plugin_name in plugins:
        job_id = "demo_" + uuid.uuid4().hex[:10]
        seed = abs(hash(plugin_name)) % 2_147_483_647
        job = Job(
            job_id=job_id,
            plugin=plugin_name,
            topic=f"Demo deck for {plugin_name.replace('_', ' ')}",
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
        db.insert_job(conn, job, seed)
        artifact = Orchestrator(cfg, resolver, registry, conn, job, seed).run()
        db.update_job_status(conn, job_id, JobStatus.REVIEW_READY, finished_at=db.iso(db.now_utc()))
        print(f"  {plugin_name}: {artifact.final_sequence.parent}")
    conn.close()
    print("Demo complete. Open the app and review the decks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
