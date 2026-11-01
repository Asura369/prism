from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ...domain import TrendCandidate


def create_manual_candidate(title: str, snippet: str = "", url: str = "") -> TrendCandidate:
    title = title.strip()
    digest = hashlib.sha256(f"{title}\n{url}".encode()).hexdigest()[:16]
    return TrendCandidate(
        id=f"manual:{digest}",
        title=title,
        source="manual",
        url=url.strip(),
        snippet=snippet.strip(),
        metrics={"score": 1.0},
        fetched_at=datetime.now(timezone.utc),
    )
