"""FoodNameResolver and alias resolution."""

from __future__ import annotations

import json

import pytest

from app.infrastructure.nutrition.food_aliases import FoodAliasIndex
from app.infrastructure.nutrition.food_name_resolver import FoodNameResolver


@pytest.fixture
def mini_resolver(tmp_path):
    def _factory(aliases: dict) -> FoodNameResolver:
        path = tmp_path / "aliases.json"
        path.write_text(
            json.dumps({"version": 2, "aliases": aliases}, ensure_ascii=False),
            encoding="utf-8",
        )
        return FoodNameResolver(FoodAliasIndex(str(path)))

    return _factory


def test_resolve_russian_alias_kartoshka(mini_resolver) -> None:
    resolver = mini_resolver(
        {
            "картошка": {
                "canonical": "potato",
                "default_state": "cooked",
                "category": "vegetable",
                "language": "ru",
            }
        }
    )
    resolved = resolver.resolve("картошка", "ru")
    assert resolved is not None
    assert resolved.canonical_name == "potato"
    assert resolved.source == "alias"
    assert resolved.confidence == 1.0


def test_resolve_unknown_returns_none(mini_resolver) -> None:
    resolver = mini_resolver({})
    assert resolver.resolve("супер еда xyz", "ru") is None


def test_alias_with_display_map(mini_resolver) -> None:
    resolver = mini_resolver(
        {
            "картошка": {
                "canonical": "potato",
                "default_state": "cooked",
                "display": {"ru": "картофель", "en": "potato"},
            }
        }
    )
    resolved = resolver.resolve("картошка", "ru")
    assert resolved is not None
    assert resolved.display_name == "картофель"
