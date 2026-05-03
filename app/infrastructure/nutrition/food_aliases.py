"""Load food_aliases.json (version + aliases map) for nutrition matching."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AliasEntry:
    canonical: str
    default_state: str
    category: str | None = None


class FoodAliasIndex:
    """Case-insensitive lookup: alias key → canonical + default_state."""

    def __init__(self, path: str | None):
        self._path = path
        self._by_norm: dict[str, AliasEntry] = {}
        if path:
            self._load(path)

    def _load(self, path: str) -> None:
        p = Path(path)
        if not p.is_file():
            logger.warning("food_aliases path missing: %s", path)
            return
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Could not parse food_aliases.json: %s", e)
            return
        aliases = raw.get("aliases") if isinstance(raw, dict) else None
        if not isinstance(aliases, dict):
            return
        for key, val in aliases.items():
            if not isinstance(key, str) or not isinstance(val, dict):
                continue
            canon = val.get("canonical")
            if not isinstance(canon, str) or not canon.strip():
                continue
            ds = val.get("default_state")
            if not isinstance(ds, str) or not ds.strip():
                ds = "unknown"
            cat = val.get("category")
            cat_s = cat.strip() if isinstance(cat, str) and cat.strip() else None
            nk = _norm_key(key)
            self._by_norm[nk] = AliasEntry(
                canonical=canon.strip(),
                default_state=ds.strip().lower(),
                category=cat_s,
            )
        logger.info("Loaded %s food alias entries from %s", len(self._by_norm), path)

    def lookup(self, name: str) -> AliasEntry | None:
        if not name or not self._by_norm:
            return None
        return self._by_norm.get(_norm_key(name))

    @property
    def is_loaded(self) -> bool:
        return bool(self._by_norm)


def _norm_key(s: str) -> str:
    return " ".join(s.strip().lower().split())
