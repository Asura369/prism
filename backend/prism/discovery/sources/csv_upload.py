from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone

from ...domain import TrendCandidate
from ...errors import InvalidTrendsCSV

QUERY_COLUMNS = {"query", "related queries", "search term", "topic"}
SCORE_COLUMNS = {"score", "search volume", "value"}


def _parse_score(raw: str) -> float:
    value = raw.strip().lower()
    if not value:
        return 0.0
    if value == "breakout":
        return 1.0
    if value.replace(" ", "") == "<1%":
        return 0.01
    value = value.replace(",", "").replace("%", "").replace("+", "").strip()
    try:
        return max(0.0, min(1.0, float(value)))
    except ValueError:
        return 0.0


def parse_trends_csv(content: bytes, filename: str) -> list[TrendCandidate]:
    """Parse a Google Trends 'Related queries' export. Raises InvalidTrendsCSV."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidTrendsCSV(f"Could not decode CSV as UTF-8: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise InvalidTrendsCSV(
            "Expected columns: query + score. Download 'Related queries' export from Google Trends."
        )

    headers = {(name or "").strip().lower(): name for name in reader.fieldnames}
    query_column = next((headers[key] for key in QUERY_COLUMNS if key in headers), None)
    score_column = next((headers[key] for key in SCORE_COLUMNS if key in headers), None)
    if query_column is None or score_column is None:
        raise InvalidTrendsCSV(
            "Expected columns: query + score. Download 'Related queries' export from Google Trends."
        )

    file_sha = hashlib.sha256(content).hexdigest()
    fetched_at = datetime.now(timezone.utc)
    candidates: list[TrendCandidate] = []
    for index, row in enumerate(reader, start=1):
        title = (row.get(query_column) or "").strip()
        if not title:
            continue
        score = _parse_score(row.get(score_column) or "")
        candidates.append(
            TrendCandidate(
                id=f"csv:{file_sha[:12]}:{index}",
                title=title,
                source="google_trends_csv",
                url="",
                snippet="",
                metrics={"score": score, "filename": filename, "sha256": file_sha},
                fetched_at=fetched_at,
            )
        )
    return candidates


class GoogleTrendsCSV:
    name = "google_trends_csv"

    @staticmethod
    def parse(content: bytes, filename: str) -> list[TrendCandidate]:
        return parse_trends_csv(content, filename)
