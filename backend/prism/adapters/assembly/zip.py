from __future__ import annotations

import zipfile
from pathlib import Path

from ..base import ImageSequenceExportAdapter


class ZipExportAdapter(ImageSequenceExportAdapter):
    name = "zip"

    def export(self, slides: list[Path], out_path: Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for index, slide in enumerate(slides, start=1):
                info = zipfile.ZipInfo(f"{index:02d}.png", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, Path(slide).read_bytes())
        return out_path
