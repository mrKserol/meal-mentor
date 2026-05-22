"""Resolve user-facing food names to canonical names for nutrition lookup."""

from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.nutrition.food_aliases import AliasEntry, FoodAliasIndex

# TODO: Add CacheFoodNameProvider backed by DB table food_alias_cache.
# TODO: Add MLFoodNameProvider for local multilingual ingredient normalization.
# TODO: Add LLMFoodNameProvider as last-resort fallback with strict JSON output.
# TODO: Add curated food_translations provider for display names by user.language.


@dataclass(frozen=True)
class ResolvedFoodName:
    input_name: str
    canonical_name: str
    display_name: str | None
    language: str | None
    default_state: str | None
    category: str | None
    source: str
    confidence: float


class FoodNameProvider:
    def resolve(self, input_name: str, language: str | None = None) -> ResolvedFoodName | None:
        raise NotImplementedError


def _display_from_entry(entry: AliasEntry, language: str | None) -> str | None:
    if not entry.display or not language:
        return None
    lang = language.strip().lower()
    val = entry.display.get(lang)
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


class AliasFoodNameProvider(FoodNameProvider):
    def __init__(self, aliases: FoodAliasIndex):
        self.aliases = aliases

    def resolve(self, input_name: str, language: str | None = None) -> ResolvedFoodName | None:
        entry = self.aliases.lookup(input_name)
        if entry is None:
            return None
        display = _display_from_entry(entry, language)
        return ResolvedFoodName(
            input_name=input_name,
            canonical_name=entry.canonical,
            display_name=display,
            language=language,
            default_state=entry.default_state,
            category=entry.category,
            source="alias",
            confidence=1.0,
        )


class FoodNameResolver:
    def __init__(self, aliases: FoodAliasIndex):
        self.aliases = aliases
        self.providers: list[FoodNameProvider] = [
            AliasFoodNameProvider(aliases),
            # later: CacheFoodNameProvider
            # later: MLFoodNameProvider
            # later: LLMFoodNameProvider
        ]

    def resolve(self, input_name: str, language: str | None = None) -> ResolvedFoodName | None:
        name = (input_name or "").strip()
        if not name:
            return None
        for provider in self.providers:
            resolved = provider.resolve(name, language=language)
            if resolved is not None:
                return resolved
        return None
