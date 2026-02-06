from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).with_suffix("").parent / "catalog.yaml"


class PreambleCatalogError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_catalog(path: str | None = None) -> dict[str, dict]:
    catalog_path = Path(path) if path else CATALOG_PATH
    if not catalog_path.is_file():
        raise PreambleCatalogError(f"Preamble catalog not found: {catalog_path}")
    import yaml

    with catalog_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):  # defensive
        raise PreambleCatalogError("Preamble catalog must be a mapping of key to entry")
    return data


def get_preamble(key: str, *, path: str | None = None) -> tuple[str, str]:
    catalog = load_catalog(path)
    entry = catalog.get(key)
    if not entry:
        raise PreambleCatalogError(f"Unknown preamble key: {key}")
    content = entry.get("content")
    version = entry.get("version") or "unknown"
    if not content:
        raise PreambleCatalogError(f"Preamble content missing for key: {key}")
    return content, version


def catalog_keys(path: str | None = None) -> list[str]:
    return sorted(load_catalog(path).keys())
