from __future__ import annotations

import importlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml

from ..adapters.resolver import AdapterResolver
from ..config import Config

log = logging.getLogger(__name__)
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ADAPTER_INTERFACE = {"llm": "llm", "cards": "cards", "export": "export", "news": "news"}


@dataclass
class PluginInfo:
    name: str
    version: str
    description: str
    output_kind: str
    defaults: dict[str, Any]
    manifest: dict[str, Any]
    available: bool
    missing_adapters: list[str] = field(default_factory=list)
    class_name: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "output_kind": self.output_kind,
            "defaults": self.defaults,
            "available": self.available,
            "missing_adapters": self.missing_adapters,
            "class_name": self.class_name,
            "manifest": self.manifest,
            "error": self.error,
        }


class PluginRegistry:
    def __init__(self, cfg: Config, resolver: AdapterResolver, plugins_dir: Path | None = None):
        self.cfg = cfg
        self.resolver = resolver
        self.plugins_dir = plugins_dir or Path(__file__).resolve().parent
        self._plugins: dict[str, Any] = {}
        self._infos: dict[str, PluginInfo] = {}
        self._scan()

    def _scan(self) -> None:
        for manifest_path in sorted(self.plugins_dir.glob("*/manifest.yaml")):
            try:
                manifest = yaml.safe_load(manifest_path.read_text()) or {}
                info = self._load_plugin(manifest_path, manifest)
                self._infos[info.name] = info
            except Exception as exc:  # noqa: BLE001 - a bad plugin must not stop the app
                log.warning("Skipping plugin at %s: %s", manifest_path, exc)

    def _load_plugin(self, path: Path, manifest: dict[str, Any]) -> PluginInfo:
        name = manifest["name"]
        entrypoint = manifest["entrypoint"]
        module_name, _, class_name = entrypoint.partition(":")
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        if cls.name != name:
            raise ValueError(f"class name {cls.name!r} does not match manifest name {name!r}")
        if not SEMVER.match(str(cls.version)):
            raise ValueError(f"invalid version {cls.version!r}")
        if cls.output_kind != manifest.get("output_kind"):
            raise ValueError("class output_kind does not match manifest")
        plugin = cls(self.cfg, self.cfg.base_dir / self.cfg.assets.styles_dir)
        plugin.attach_manifest(manifest)

        missing: list[str] = []
        for asset in manifest.get("assets", []):
            hint = asset.get("adapter")
            interface = ADAPTER_INTERFACE.get(hint or "")
            if interface and not self.resolver.resolve(interface):
                missing.append(hint)
        info = PluginInfo(
            name=name,
            version=str(cls.version),
            description=manifest.get("description", ""),
            output_kind=cls.output_kind,
            defaults=manifest.get("defaults", {}),
            manifest=manifest,
            available=not missing,
            missing_adapters=sorted(set(missing)),
            class_name=class_name,
        )
        self._plugins[name] = plugin
        return info

    def list_plugins(self) -> list[PluginInfo]:
        return list(self._infos.values())

    def get_info(self, name: str) -> PluginInfo | None:
        return self._infos.get(name)

    def get(self, name: str):
        return self._plugins.get(name)

    def names(self) -> list[str]:
        return list(self._plugins.keys())

    def stages_for(self, name: str) -> list[str]:
        stages = ["spec", "render", "export", "metadata", "policy", "validate", "publish"]
        info = self._infos.get(name)
        if info and (info.manifest.get("ingest") or any(a.get("adapter") == "news" for a in info.manifest.get("assets", []))):
            stages.insert(1, "ingest")
        return stages
