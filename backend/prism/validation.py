from __future__ import annotations

import zipfile
from pathlib import Path

from PIL import Image

from .config import Config
from .domain import ContentSpec


def validate_sequence(zip_path: Path, spec: ContentSpec, cfg: Config, styles_dir: Path | None = None) -> list[str]:
    """Return a list of failure reasons. Empty list means the artifact passes."""
    reasons: list[str] = []
    zip_path = Path(zip_path)
    expected = [f"{i:02d}.png" for i in range(1, len(spec.slides) + 1)]
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.endswith(".png")]
            if sorted(names) != sorted(expected):
                reasons.append(f"Zip PNGs {sorted(names)} do not match expected {expected}")
                return reasons
            width, height = spec.resolution.lower().split("x")
            expected_size = (int(width), int(height))
            total_size = 0
            for name in expected:
                data = zf.read(name)
                total_size += len(data)
                try:
                    from io import BytesIO

                    with Image.open(BytesIO(data)) as img:
                        if img.size != expected_size:
                            reasons.append(f"{name} is {img.size}, expected {expected_size}")
                except Exception as exc:  # noqa: BLE001
                    reasons.append(f"{name} does not open: {exc}")
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"Zip does not open: {exc}"]

    if total_size < cfg.validation.min_file_size_mb * 1024 * 1024:
        reasons.append(f"Artifact is smaller than {cfg.validation.min_file_size_mb} MB")
    if any(not (slide.alt_text or "").strip() for slide in spec.slides):
        reasons.append("Every slide must have non-empty alt text")
    if len(spec.caption) > cfg.validation.caption_max_chars:
        reasons.append(f"Caption exceeds {cfg.validation.caption_max_chars} characters")
    if len(spec.hashtags) > cfg.validation.hashtags_max:
        reasons.append(f"More than {cfg.validation.hashtags_max} hashtags")
    if not (cfg.validation.min_slide_count <= len(spec.slides) <= cfg.validation.max_slide_count):
        reasons.append(
            f"Slide count {len(spec.slides)} outside "
            f"[{cfg.validation.min_slide_count}, {cfg.validation.max_slide_count}]"
        )
    styles_dir = styles_dir or Path(cfg.assets.styles_dir)
    if not (styles_dir / f"{spec.style}.yaml").exists():
        reasons.append(f"Style preset {spec.style!r} not found")
    return reasons
