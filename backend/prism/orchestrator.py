from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from . import db
from .adapters.resolver import AdapterResolver
from .config import Config
from .domain import Artifact, Job, JobStatus
from .errors import (
    InsufficientSourcesError,
    JobCancelled,
    PolicyViolation,
    SpecValidationError,
    ValidationError,
)
from .plugins.base import RenderContext, extract_json
from .plugins.registry import PluginRegistry
from .validation import validate_sequence

log = logging.getLogger(__name__)

STAGE_WEIGHTS = {
    "spec": 0.10,
    "ingest": 0.10,
    "render": 0.55,
    "export": 0.05,
    "metadata": 0.10,
    "policy": 0.05,
    "validate": 0.03,
    "publish": 0.02,
}

STAGE_MESSAGES = {
    "spec": "Writing the deck spec",
    "ingest": "Collecting sources",
    "render": "Rendering slides",
    "export": "Packaging carousel",
    "metadata": "Writing caption and alt text",
    "policy": "Checking policy",
    "validate": "Validating artifact",
    "publish": "Publishing to review",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Orchestrator:
    def __init__(
        self,
        cfg: Config,
        resolver: AdapterResolver,
        registry: PluginRegistry,
        conn: sqlite3.Connection,
        job: Job,
        seed: int,
        recommended_plugin: str | None = None,
    ):
        self.cfg = cfg
        self.resolver = resolver
        self.registry = registry
        self.conn = conn
        self.job = job
        self.seed = seed
        self.recommended_plugin = recommended_plugin
        self.plugin = registry.get(job.plugin)
        if self.plugin is None:
            raise SpecValidationError(f"Plugin not installed: {job.plugin}", stage="spec")
        self.work_dir = cfg.base_dir / cfg.run.work_dir / job.job_id
        self.out_dir = cfg.base_dir / cfg.run.output_dir / job.job_id
        self.stages = registry.stages_for(job.plugin)
        self.weight_total = sum(STAGE_WEIGHTS[s] for s in self.stages)
        self.spec = None
        self.assets = []
        self.recipe = None
        self.zip_path: Path | None = None
        self.retries: list[dict[str, Any]] = []
        self.llm_adapter_name: str | None = None
        self.llm_model: str | None = None
        self.manifest: dict[str, Any] = {
            "job_id": job.job_id,
            "plugin": job.plugin,
            "plugin_version": self.plugin.version,
            "output_kind": self.plugin.output_kind,
            "topic": job.topic,
            "angle": job.angle,
            "created_at": db.iso(job.created_at),
            "started_at": None,
            "finished_at": None,
            "status": "RUNNING",
            "recommended_plugin": recommended_plugin,
            "user_accepted_recommendation": job.plugin == recommended_plugin if recommended_plugin else None,
            "degraded": False,
            "fallbacks_used": [],
            "adapters": {},
            "prompt_hashes": {},
            "retries": self.retries,
            "sources": [],
            "stages": [],
            "error": None,
        }

    # ---- progress + cancellation -------------------------------------------------
    def _progress(self, stage: str, frac: float) -> float:
        prior = 0.0
        for name in self.stages:
            if name == stage:
                break
            prior += STAGE_WEIGHTS[name]
        raw = (prior + STAGE_WEIGHTS[stage] * max(0.0, min(1.0, frac))) / self.weight_total
        return round(min(1.0, raw), 4)

    def emit(self, stage: str, frac: float, message: str) -> None:
        row = db.get_job(self.conn, self.job.job_id)
        if row and row.status == JobStatus.CANCELLED:
            raise JobCancelled("Job was cancelled")
        progress = self._progress(stage, frac)
        db.update_job(self.conn, self.job.job_id, stage=stage, progress=progress, heartbeat_at=db.iso(db.now_utc()))
        db.append_event(self.conn, self.job.job_id, stage=stage, progress=progress, message=message)

    def _stage(self, name: str, fn) -> None:
        self.emit(name, 0.0, STAGE_MESSAGES[name])
        result = fn()
        self.emit(name, 1.0, f"{name} complete")
        return result

    # ---- LLM helper --------------------------------------------------------------
    def _llm(self, prompt: str, *, json_schema: dict[str, Any] | None, purpose: str) -> str:
        self.manifest["prompt_hashes"][purpose] = sha256_text(prompt)
        result = self.resolver.complete(prompt, json_schema=json_schema)
        self.retries.extend({**failure, "purpose": purpose} for failure in result.failures)
        if self.llm_adapter_name is None:
            self.llm_adapter_name = result.adapter
            self.llm_model = result.model
        if result.adapter == "stub" or result.adapter != self.resolver.llm_name:
            # Stub output is canned even when it is the expected adapter (testing mode).
            label = f"llm:{result.adapter}"
            if label not in self.manifest["fallbacks_used"]:
                self.manifest["fallbacks_used"].append(label)
            self.manifest["degraded"] = True
        return result.text

    # ---- stages ------------------------------------------------------------------
    def _do_spec(self) -> None:
        prompt = self.plugin.spec_prompt(self.job.topic, self.job.angle)
        schema = self.plugin.spec_schema()
        output = self._llm(prompt, json_schema=schema, purpose="spec")
        try:
            spec = self.plugin.parse_spec(output)
        except SpecValidationError as exc:
            retry_prompt = (
                f"{prompt}\n\nYour previous response was invalid: {exc.message}\n"
                "Fix every violation and return corrected JSON only."
            )
            self.emit("spec", 0.6, "Spec failed validation; re-prompting once")
            output = self._llm(retry_prompt, json_schema=schema, purpose="spec_retry")
            spec = self.plugin.parse_spec(output)

        style = self.job.overrides.get("style")
        if style:
            available = self.resolver.style_names()
            if style not in available:
                raise SpecValidationError(f"Unknown style {style!r}; available: {available}", stage="spec")
            spec.style = style
        self.spec = spec
        self.manifest["style"] = spec.style
        self.manifest["resolution"] = spec.resolution
        self.manifest["title"] = spec.title

    def _do_ingest(self) -> None:
        params = self.plugin.ingest_config.get("params", {})
        max_articles = params.get("max_articles", 5)
        language = params.get("language", "en")
        min_sources = self.plugin.policy_config.get("min_sources", 2)

        adapter = None
        articles: list[dict[str, Any]] = []
        failed_adapters: list[str] = []
        for candidate in self.resolver.require("news"):
            try:
                articles = candidate.fetch_articles(  # type: ignore[union-attr]
                    query=self.job.topic, max_articles=max_articles, language=language
                )
            except Exception as exc:  # noqa: BLE001 - adapter boundary
                name = getattr(candidate, "name", "?")
                log.warning("news adapter %s failed: %s", name, exc)
                failed_adapters.append(name)
                self.manifest.setdefault("ingest_errors", []).append({"adapter": name, "error": str(exc)})
                continue
            if articles:
                adapter = candidate
                break

        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for article in articles:
            if article["url"] in seen:
                continue
            seen.add(article["url"])
            unique.append(article)
        if len(unique) < min_sources:
            raise InsufficientSourcesError(len(unique), min_sources)

        self.spec.sources = [{"name": a["source_name"], "url": a["url"]} for a in unique]
        self.spec.slides = self.plugin.build_slides(self.spec)
        self.manifest["ingest"] = {
            "adapter": "news",
            "params": params,
            "sources": self.spec.sources,
            "failed_adapters": failed_adapters,
        }
        self.manifest["sources"] = self.spec.sources
        self.manifest["adapters"]["news"] = {"name": getattr(adapter, "name", "?")}
        news_name = getattr(adapter, "name", None)
        if news_name == "stub" or news_name != self.resolver.chain_names("news")[0]:
            label = f"news:{getattr(adapter, 'name', '?')}"
            if label not in self.manifest["fallbacks_used"]:
                self.manifest["fallbacks_used"].append(label)
            self.manifest["degraded"] = True

    def _do_render(self) -> None:
        ctx = RenderContext(
            job=self.job,
            work_dir=self.work_dir,
            resolver=self.resolver,
            emit=self.emit,
            seed=self.seed,
            sources=self.spec.sources,
        )
        self.assets = self.plugin.build_assets(self.spec, ctx)
        self.recipe = self.plugin.build_recipe(self.spec, self.assets)
        cards = self.resolver.get("cards")
        self.manifest["adapters"]["cards"] = {"name": getattr(cards, "name", "?"), "style": self.spec.style}
        self.manifest["slides"] = [
            {"index": a.meta.get("index"), "sha256": a.meta.get("sha256"), "file": a.path.name}
            for a in self.assets
        ]

    def _do_export(self) -> None:
        target = self.work_dir / self.recipe.out_zip_name
        exporter = self.resolver.get("export")
        self.zip_path = Path(exporter.export(self.recipe.slides, target))
        self.manifest["adapters"]["export"] = {"name": getattr(exporter, "name", "?")}

    def _do_metadata(self) -> None:
        fallback_caption = self._default_caption()
        fallback_hashtags = [
            "learnsomethingnew", "didyouknow", "facts", "explainer", "curiosity",
        ]
        prompt = self.plugin.metadata_prompt(self.spec, self.assets)
        try:
            output = self._llm(prompt, json_schema=None, purpose="metadata")
            data = extract_json(output)
            if not isinstance(data, dict):
                raise ValueError("metadata response is not an object")
            caption = str(data.get("caption") or fallback_caption)
            hashtags = [str(h).lstrip("#").strip() for h in data.get("hashtags", []) if str(h).strip()]
            alt_texts = data.get("alt_text") if isinstance(data.get("alt_text"), list) else []
        except Exception:  # noqa: BLE001 - metadata never blocks a job
            caption, hashtags, alt_texts = fallback_caption, fallback_hashtags, []

        self.spec.caption = caption[: self.cfg.validation.caption_max_chars]
        self.spec.caption = self.plugin.finalize_caption(self.spec.caption, self.spec)
        self.spec.hashtags = hashtags[: self.cfg.validation.hashtags_max] or fallback_hashtags
        for index, slide in enumerate(self.spec.slides):
            provided = str(alt_texts[index]).strip() if index < len(alt_texts) and alt_texts[index] else ""
            slide.alt_text = provided or self._derive_alt(slide)

    def _derive_alt(self, slide) -> str:
        text = f"{slide.kind} slide. {slide.heading}."
        if slide.body:
            text += f" {slide.body}"
        return text[:300]

    def _default_caption(self) -> str:
        headings = " ".join(f"{i + 1}. {s.heading}." for i, s in enumerate(self.spec.slides[:3]))
        return f"{self.spec.title}. {headings} Follow for more."[: self.cfg.validation.caption_max_chars]

    def _do_policy(self) -> None:
        result = self.plugin.policy_check(self.spec, self.assets, self.spec.sources)
        errors = list(result.reasons)
        if "ai_disclosure" in self.plugin.policy_config:
            self.manifest["ai_disclosure"] = True
        if errors:
            raise PolicyViolation(errors)

    def _do_validate(self) -> None:
        reasons = validate_sequence(self.zip_path, self.spec, self.cfg, self.cfg.base_dir / self.cfg.assets.styles_dir)
        if reasons:
            raise ValidationError(reasons)

    def _metadata_json(self) -> dict[str, Any]:
        return {
            "title": self.spec.title,
            "caption": self.spec.caption,
            "hashtags": self.spec.hashtags,
            "platforms": ["instagram_feed"],
            "ai_disclosure": True,
            "alt_text": [slide.alt_text for slide in self.spec.slides],
        }

    def _do_publish(self) -> Artifact:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = self.work_dir / "metadata.json"
        manifest_path = self.work_dir / "manifest.json"
        status_path = self.work_dir / "status.json"
        thumbnail_path = self.work_dir / "thumbnail.png"

        self.manifest["status"] = "REVIEW_READY"
        self.manifest["finished_at"] = db.iso(db.now_utc())
        self.manifest["adapters"]["llm"] = {
            "name": self.llm_adapter_name or "stub",
            "model": self.llm_model or "stub",
        }

        metadata = self._metadata_json()
        metadata_path.write_text(json.dumps(metadata, indent=2))
        manifest_path.write_text(json.dumps(self.manifest, indent=2, default=str))
        status_path.write_text(
            json.dumps(
                {
                    "job_id": self.job.job_id,
                    "plugin": self.job.plugin,
                    "status": "REVIEW_READY",
                    "published_at": db.iso(db.now_utc()),
                },
                indent=2,
            )
        )
        shutil.copyfile(self.recipe.slides[0], thumbnail_path)

        self.out_dir.parent.mkdir(parents=True, exist_ok=True)
        if self.out_dir.exists():
            raise FileExistsError(f"Review directory already exists: {self.out_dir}")
        os.replace(self.work_dir, self.out_dir)

        db.upsert_review_meta(self.conn, self.job.job_id, metadata=metadata, manifest=self.manifest)
        return Artifact(
            job_id=self.job.job_id,
            output_kind=self.spec.output_kind,
            final_sequence=self.out_dir / self.recipe.out_zip_name,
            thumbnail=self.out_dir / "thumbnail.png",
            metadata=self.out_dir / "metadata.json",
            manifest=self.out_dir / "manifest.json",
            status=self.out_dir / "status.json",
        )

    # ---- run ---------------------------------------------------------------------
    def run(self) -> Artifact:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.manifest["started_at"] = db.iso(db.now_utc())
        self.manifest["stages"] = [{"name": s, "status": "pending", "progress": 0.0} for s in self.stages]
        handlers = {
            "spec": self._do_spec,
            "ingest": self._do_ingest,
            "render": self._do_render,
            "export": self._do_export,
            "metadata": self._do_metadata,
            "policy": self._do_policy,
            "validate": self._do_validate,
            "publish": self._do_publish,
        }
        try:
            for index, stage in enumerate(self.stages):
                entry = self.manifest["stages"][index]
                entry["status"] = "running"
                artifact = self._stage(stage, handlers[stage])
                entry["status"] = "completed"
                entry["progress"] = 1.0
            self.manifest["status"] = "REVIEW_READY"
            return artifact
        except JobCancelled:
            raise
        except Exception as exc:
            self.manifest["status"] = "FAILED"
            self.manifest["error"] = exc.to_dict() if hasattr(exc, "to_dict") else {
                "error_class": exc.__class__.__name__,
                "stage": getattr(exc, "stage", None),
                "message": str(exc),
                "retryable": False,
                "context": {},
            }
            self.manifest["finished_at"] = db.iso(db.now_utc())
            try:
                self.work_dir.mkdir(parents=True, exist_ok=True)
                (self.work_dir / "manifest.json").write_text(json.dumps(self.manifest, indent=2, default=str))
            except OSError:
                pass
            raise
