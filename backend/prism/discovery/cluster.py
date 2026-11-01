from __future__ import annotations

import hashlib
from difflib import SequenceMatcher

from ..domain import TrendCandidate


def _representative_score(candidate: TrendCandidate, reliability: dict[str, float]) -> float:
    recency = max(0.1, float(candidate.metrics.get("recency_h", 24.0)))
    return reliability.get(candidate.source, 0.7) * recency ** -0.5


def cluster(
    candidates: list[TrendCandidate],
    threshold: float = 0.80,
    source_reliability: dict[str, float] | None = None,
) -> list[TrendCandidate]:
    """Collapse near-duplicate titles, returning one representative per cluster."""
    reliability = source_reliability or {}
    groups: list[list[TrendCandidate]] = []
    for candidate in candidates:
        for group in groups:
            if SequenceMatcher(None, group[0].title.lower(), candidate.title.lower()).ratio() > threshold:
                group.append(candidate)
                break
        else:
            groups.append([candidate])

    representatives: list[TrendCandidate] = []
    for group in groups:
        rep = max(group, key=lambda candidate: _representative_score(candidate, reliability))
        cluster_id = "c:" + hashlib.sha1(rep.id.encode()).hexdigest()[:12]
        for member in group:
            member.cluster_id = cluster_id
        rep.metrics["cluster_size"] = len(group)
        rep.metrics["cluster_members"] = [
            {"id": member.id, "title": member.title, "source": member.source} for member in group
        ]
        representatives.append(rep)
    return representatives
