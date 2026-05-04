#!/usr/bin/env python3
"""Merge domain aliases into data/food_aliases.json (run from repo root)."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    path = root / "data" / "food_aliases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    aliases = data.setdefault("aliases", {})
    if not isinstance(aliases, dict):
        raise SystemExit("invalid aliases")

    updates: dict[str, dict[str, str]] = {
        # Eggs — fried / Russian
        "fried eggs": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "fried egg": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "scrambled eggs": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "яичница": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "жареные яйца": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "жареное яйцо": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "яйцо жареное": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        "яйца жареные": {"canonical": "Egg, fried, cooked, whole", "default_state": "fried", "category": "egg"},
        # White beans — prefer boiled mature white
        "white beans": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "cooked white beans": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "boiled white beans": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "фасоль": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "белая фасоль": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "фасоль вареная": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "фасоль варёная": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "отварная фасоль": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        "фасоль готовая": {
            "canonical": "Beans, without salt, boiled, cooked, mature seeds, white",
            "default_state": "cooked",
            "category": "legume",
        },
        # Buckwheat — cooked default (overrides generic "Buckwheat")
        "buckwheat": {
            "canonical": "Buckwheat groats, cooked, roasted",
            "default_state": "cooked",
            "category": "grain",
        },
        "cooked buckwheat": {
            "canonical": "Buckwheat groats, cooked, roasted",
            "default_state": "cooked",
            "category": "grain",
        },
        "buckwheat groats": {
            "canonical": "Buckwheat groats, cooked, roasted",
            "default_state": "cooked",
            "category": "grain",
        },
        "dry buckwheat": {
            "canonical": "Buckwheat groats, dry, roasted",
            "default_state": "dry",
            "category": "grain",
        },
        "buckwheat dry": {
            "canonical": "Buckwheat groats, dry, roasted",
            "default_state": "dry",
            "category": "grain",
        },
        "сухая гречка": {
            "canonical": "Buckwheat groats, dry, roasted",
            "default_state": "dry",
            "category": "grain",
        },
        "гречка сухая": {
            "canonical": "Buckwheat groats, dry, roasted",
            "default_state": "dry",
            "category": "grain",
        },
        "гречневая крупа сухая": {
            "canonical": "Buckwheat groats, dry, roasted",
            "default_state": "dry",
            "category": "grain",
        },
        # Chicken breast — disambiguate cuts / prep
        "chicken breast": {
            "canonical": "Chicken, roasted, cooked, meat only, broilers or fryers",
            "default_state": "cooked",
            "category": "poultry",
        },
        "fried chicken breast": {
            "canonical": "Chicken, fried, cooked, meat only, breast, broilers or fryers",
            "default_state": "fried",
            "category": "poultry",
        },
        "grilled chicken breast": {
            "canonical": "Chicken, grilled, cooked, meat only, boneless, skinless, breast, broiler or fryers",
            "default_state": "grilled",
            "category": "poultry",
        },
        "cooked chicken breast": {
            "canonical": "Chicken, roasted, cooked, meat only, broilers or fryers",
            "default_state": "cooked",
            "category": "poultry",
        },
        "куриная грудка": {
            "canonical": "Chicken, roasted, cooked, meat only, broilers or fryers",
            "default_state": "cooked",
            "category": "poultry",
        },
        "жареная куриная грудка": {
            "canonical": "Chicken, fried, cooked, meat only, breast, broilers or fryers",
            "default_state": "fried",
            "category": "poultry",
        },
        "курица грудка": {
            "canonical": "Chicken, roasted, cooked, meat only, broilers or fryers",
            "default_state": "cooked",
            "category": "poultry",
        },
        "филе курицы": {
            "canonical": "Chicken, roasted, cooked, meat only, broilers or fryers",
            "default_state": "cooked",
            "category": "poultry",
        },
        "куриное филе": {
            "canonical": "Chicken, roasted, cooked, meat only, broilers or fryers",
            "default_state": "cooked",
            "category": "poultry",
        },
        # Feta / olives
        "feta cheese": {"canonical": "Cheese, feta", "default_state": "unknown", "category": "cheese"},
        "feta": {"canonical": "Cheese, feta", "default_state": "unknown", "category": "cheese"},
        "фета": {"canonical": "Cheese, feta", "default_state": "unknown", "category": "cheese"},
        "olives": {
            "canonical": "Olives, canned (small-extra large), ripe",
            "default_state": "canned",
            "category": "vegetable",
        },
        "olive": {
            "canonical": "Olives, canned (small-extra large), ripe",
            "default_state": "canned",
            "category": "vegetable",
        },
        "оливки": {
            "canonical": "Olives, canned (small-extra large), ripe",
            "default_state": "canned",
            "category": "vegetable",
        },
        "маслины": {
            "canonical": "Olives, canned (small-extra large), ripe",
            "default_state": "canned",
            "category": "vegetable",
        },
        "консервированные оливки": {
            "canonical": "Olives, canned (small-extra large), ripe",
            "default_state": "canned",
            "category": "vegetable",
        },
        "консервированные маслины": {
            "canonical": "Olives, canned (small-extra large), ripe",
            "default_state": "canned",
            "category": "vegetable",
        },
    }

    for key, meta in updates.items():
        nk = " ".join(key.strip().lower().split())
        aliases[nk] = dict(meta)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("patched", path, "aliases count", len(aliases))


if __name__ == "__main__":
    main()
