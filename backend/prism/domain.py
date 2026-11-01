from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    REVIEW_READY = "REVIEW_READY"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OutputKind(str, Enum):
    IMAGE_SEQUENCE = "image_sequence"


@dataclass
class Job:
    job_id: str
    plugin: str
    topic: str
    angle: dict[str, Any] | None
    overrides: dict[str, Any]
    status: JobStatus
    stage: str | None
    progress: float
    error: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@dataclass
class TrendCandidate:
    id: str
    title: str
    source: str
    url: str
    snippet: str
    metrics: dict[str, float]
    fetched_at: datetime
    cluster_id: str | None = None


@dataclass
class TrendScore:
    heuristic: float
    safety: float
    visual_potential: float
    angle_ability: float
    saturation: float
    combined: float
    reasoning: str


@dataclass
class ScoredCandidate:
    candidate: TrendCandidate
    score: TrendScore


@dataclass
class Angle:
    hook: str
    framing: str
    target_emotion: str
    format_suggestion: str
    est_slide_count: int
    why_it_works: str
    recommended_plugin: str
    plugin_reasoning: str


@dataclass
class SlideSpec:
    kind: str
    heading: str
    body: str | None
    meta: dict[str, Any] = field(default_factory=dict)
    alt_text: str = ""


@dataclass
class ContentSpec:
    raw: dict[str, Any]
    slides: list[SlideSpec]
    aspect_ratio: str
    resolution: str
    style: str
    title: str
    caption: str
    hashtags: list[str]
    output_kind: OutputKind
    sources: list[dict] = field(default_factory=list)


@dataclass
class AssetRequest:
    kind: str
    adapter_hint: str | None
    params: dict[str, Any]


@dataclass
class Asset:
    kind: str
    path: Path
    meta: dict[str, Any]


@dataclass
class ImageSequenceRecipe:
    slides: list[Path]
    style: str
    resolution: str
    out_zip_name: str = "carousel.zip"


@dataclass
class Artifact:
    job_id: str
    output_kind: OutputKind
    final_sequence: Path
    thumbnail: Path
    metadata: Path
    manifest: Path
    status: Path


@dataclass
class PolicyResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
