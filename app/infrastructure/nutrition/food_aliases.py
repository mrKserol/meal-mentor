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
    language: str | None = None
    display: dict[str, str] | None = None


class FoodAliasIndex:
    """Case-insensitive lookup: alias key → canonical + default_state."""

    def __init__(self, path: str | None):
        self._path = path
        self._by_norm: dict[str, AliasEntry] = {}
        self._ru_name_by_canonical: dict[str, str] = {}
        self._ru_name_rank_by_canonical: dict[str, tuple[int, int]] = {}
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
            lang = val.get("language")
            lang_s = lang.strip().lower() if isinstance(lang, str) and lang.strip() else None
            display_raw = val.get("display")
            display_map: dict[str, str] | None = None
            if isinstance(display_raw, dict):
                display_map = {}
                for dk, dv in display_raw.items():
                    if isinstance(dk, str) and isinstance(dv, str) and dk.strip() and dv.strip():
                        display_map[dk.strip().lower()] = dv.strip()
                if not display_map:
                    display_map = None
            nk = _norm_key(key)
            self._by_norm[nk] = AliasEntry(
                canonical=canon.strip(),
                default_state=ds.strip().lower(),
                category=cat_s,
                language=lang_s,
                display=display_map,
            )
            if _has_cyrillic(key):
                canon_s = canon.strip()
                rank = _ru_alias_rank(key)
                prev_rank = self._ru_name_rank_by_canonical.get(canon_s)
                if prev_rank is None or rank > prev_rank:
                    self._ru_name_by_canonical[canon_s] = key.strip()
                    self._ru_name_rank_by_canonical[canon_s] = rank
        logger.info("Loaded %s food alias entries from %s", len(self._by_norm), path)

    def lookup(self, name: str) -> AliasEntry | None:
        if not name or not self._by_norm:
            return None
        return self._by_norm.get(_norm_key(name))

    def russian_display_for(self, english_key: str) -> str | None:
        """Best-effort Russian UI label for an English ingredient key."""
        entry = self.lookup(english_key)
        if entry is None:
            return None
        if entry.display:
            ru = entry.display.get("ru")
            if isinstance(ru, str) and ru.strip():
                return ru.strip()
        return self._ru_name_by_canonical.get(entry.canonical)

    @property
    def is_loaded(self) -> bool:
        return bool(self._by_norm)


def _has_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04FF" for ch in text)


def _ru_alias_rank(key: str) -> tuple[int, int]:
    """Prefer one-word Russian aliases with a typical short label length (~6 chars)."""
    k = key.strip()
    single_word = 1 if " " not in k else 0
    sweet_spot = -abs(len(k) - 6)
    return (single_word, sweet_spot)


def _norm_key(s: str) -> str:
    return " ".join(s.strip().lower().split())
