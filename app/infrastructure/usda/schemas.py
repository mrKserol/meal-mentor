from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UsdaMatchResult:
    input_name: str
    query: str
    grams: int
    state: str
    selected_fdc_id: int | None
    selected_description: str | None
    selected_data_type: str | None
    match_score: float
    match_status: str
    nutrients_per_100g: dict[str, float] = field(default_factory=dict)
    nutrients_scaled: dict[str, float] = field(default_factory=dict)
    candidates: list[dict] = field(default_factory=list)
    raw_food_json: dict | None = None
    food_category: str | None = None
