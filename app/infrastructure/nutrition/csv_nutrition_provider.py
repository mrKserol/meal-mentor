import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches
from typing import Any

import pandas as pd

from app.core.config import FOOD_ALIASES_PATH, NUTRITION_CSV_PATH, NUTRITION_ENABLE_SEMANTIC
from app.infrastructure.nutrition.food_aliases import FoodAliasIndex
from app.infrastructure.nutrition.ingredient_input import (
    NormalizedIngredient,
    is_grain_like_ingredient,
    is_legume_like_ingredient,
    is_poultry_breast_query,
    parse_ingredients_dict,
)
from app.infrastructure.nutrition.state_match import state_score

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz, process as rf_process

    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False

try:
    from sentence_transformers import SentenceTransformer, util

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

_SKIP_SCALE_KEYS = frozenset(
    {
        "name",
        "csv_display_name",
        "match",
        "weight",
        "state",
        "match_score",
        "candidates",
    }
)


def _parse_cell_to_float(val: Any) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    s = str(val).strip().lower()
    if not s or s in ("nan", "none", "null"):
        return 0.0
    s = s.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    if not m:
        return 0.0
    try:
        return float(m.group())
    except ValueError:
        return 0.0


_INT_ROUND_KEYS = frozenset(
    {"calories", "proteins", "fats", "carbohydrates", "fiber_g", "sugar_g", "sodium_mg"}
)


def _round_scaled(key: str, value: float) -> float | int:
    if key in _INT_ROUND_KEYS:
        return int(round(value))
    return round(value, 3)


@dataclass
class NutritionCandidate:
    name_key: str
    display_name: str
    text_score: float
    state_score: float = 0.0
    final_score: float = 0.0
    reasons: list[str] = field(default_factory=list)


class NutritionService:
    """Lookup nutrition per 100g with state-aware fuzzy candidate search."""

    def __init__(self, dataset_path: str | None = None, aliases_path: str | None = None):
        self._path = dataset_path or NUTRITION_CSV_PATH
        self._aliases: FoodAliasIndex = FoodAliasIndex(aliases_path or FOOD_ALIASES_PATH)
        self._data: dict[str, dict[str, Any]] = {}
        self._ingredients: list[str] = []
        self._model = None
        self._embeddings = None
        self._semantic_load_failed = False
        if self._path:
            self._load_data()

    def _series(self, df: pd.DataFrame, col: str) -> pd.Series:
        if col not in df.columns:
            return pd.Series([0.0] * len(df), index=df.index)
        return df[col].map(_parse_cell_to_float)

    def _load_data(self) -> None:
        df = pd.read_csv(self._path)
        data = pd.DataFrame(index=df.index)
        data["csv_display_name"] = df["name"].astype(str)
        data["name"] = df["name"].astype(str).str.lower()

        data["calories"] = self._series(df, "calories")
        data["proteins"] = self._series(df, "protein")
        data["fats"] = self._series(df, "total_fat")
        data["carbohydrates"] = self._series(df, "carbohydrate")
        data["fiber_g"] = self._series(df, "fiber")
        data["sugar_g"] = self._series(df, "sugars")
        data["saturated_fat_g"] = self._series(df, "saturated_fat")
        data["sodium_mg"] = self._series(df, "sodium")
        data["calcium_mg"] = self._series(df, "calcium")
        data["magnesium_mg"] = self._series(df, "magnesium")
        data["potassium_mg"] = self._series(df, "potassium")
        data["phosphorus_mg"] = self._series(df, "phosphorus")
        data["iron_mg"] = self._series(df, "iron")
        data["zinc_mg"] = self._series(df, "zinc")
        data["selenium_mcg"] = self._series(df, "selenium")
        data["copper_mg"] = self._series(df, "copper")
        data["manganese_mg"] = self._series(df, "manganese")
        if "vitamin_a_rae" in df.columns:
            data["vitamin_a_mcg"] = self._series(df, "vitamin_a_rae")
        else:
            data["vitamin_a_mcg"] = self._series(df, "vitamin_a")
        data["vitamin_c_mg"] = self._series(df, "vitamin_c")
        data["vitamin_d_mcg"] = self._series(df, "vitamin_d")
        data["vitamin_e_mg"] = self._series(df, "vitamin_e")
        data["vitamin_k_mcg"] = self._series(df, "vitamin_k")
        data["vitamin_b6_mg"] = self._series(df, "vitamin_b6")
        data["vitamin_b12_mcg"] = self._series(df, "vitamin_b12")
        data["folate_mcg"] = self._series(df, "folate")
        data["thiamin_mg"] = self._series(df, "thiamin")
        data["riboflavin_mg"] = self._series(df, "riboflavin")
        data["niacin_mg"] = self._series(df, "niacin")
        data["pantothenic_acid_mg"] = self._series(df, "pantothenic_acid")
        data["choline_mg"] = self._series(df, "choline")

        dataset = data.set_index("name")
        self._data = dataset.to_dict("index")
        self._ingredients = list(self._data.keys())

    def _ensure_semantic_model(self) -> bool:
        if not NUTRITION_ENABLE_SEMANTIC:
            return False
        if not _HAS_SENTENCE_TRANSFORMERS or not self._ingredients:
            return False
        if self._embeddings is not None:
            return True
        if self._semantic_load_failed:
            return False
        try:
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._embeddings = self._model.encode(
                self._ingredients,
                convert_to_tensor=True,
            )
            return True
        except Exception as e:
            self._semantic_load_failed = True
            logger.warning(
                "Semantic nutrition search disabled (could not load model): %s",
                e,
            )
            return False

    def _fuzzy_match(self, name: str, threshold: float = 0.6) -> str | None:
        q = name.lower().strip()
        matches = get_close_matches(q, self._data.keys(), n=1, cutoff=threshold)
        if not matches and q.endswith("s"):
            matches = get_close_matches(q[:-1], self._data.keys(), n=1, cutoff=threshold)
        return matches[0] if matches else None

    def _semantic_match(self, name: str, threshold: float = 0.6) -> str | None:
        if not self._ensure_semantic_model() or self._embeddings is None:
            return None
        q = name.lower().strip()
        try:
            query_emb = self._model.encode(q, convert_to_tensor=True)
        except Exception:
            return None
        cos_scores = util.pytorch_cos_sim(query_emb, self._embeddings)[0]
        best_val, best_idx = cos_scores.max(0)
        if float(best_val) < threshold:
            return None
        return self._ingredients[int(best_idx)]

    def _candidate_search(self, query: str, limit: int = 20) -> list[tuple[str, float]]:
        q = (query or "").strip()
        if not q or not self._ingredients:
            return []
        if _HAS_RAPIDFUZZ:
            extracted = rf_process.extract(q, self._ingredients, scorer=fuzz.WRatio, limit=limit)
            out: list[tuple[str, float]] = []
            for row in extracted:
                out.append((str(row[0]), float(row[1])))
            return out
        matches = get_close_matches(q.lower(), self._ingredients, n=limit, cutoff=0.35)
        scored: list[tuple[str, float]] = []
        for m in matches:
            ratio = SequenceMatcher(None, q.lower(), m).ratio() * 100
            scored.append((m, ratio))
        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    def _exact_row_bonus(self, canonical_query: str, display_name: str) -> tuple[float, list[str]]:
        reasons: list[str] = []
        cq = canonical_query.strip().lower()
        dn = display_name.strip().lower()
        if cq and dn == cq:
            reasons.append("+50:exact_canonical_row")
            return 50.0, reasons
        return 0.0, reasons

    def _rerank_candidates(
        self,
        ni: NormalizedIngredient,
        raw_candidates: list[tuple[str, float]],
    ) -> list[NutritionCandidate]:
        grain = is_grain_like_ingredient(ni)
        legume = is_legume_like_ingredient(ni)
        poultry_breast = is_poultry_breast_query(ni)
        out: list[NutritionCandidate] = []
        for name_key, text_score in raw_candidates:
            row = self._data.get(name_key) or {}
            display = str(row.get("csv_display_name") or name_key)
            st, st_reasons = state_score(
                ni.state,
                display,
                query=ni.canonical_query,
                ingredient_input=ni.input_name,
                is_grain_like=grain,
                is_legume_like=legume,
                is_poultry_breast_query=poultry_breast,
            )
            exact_bonus, exact_reasons = self._exact_row_bonus(ni.canonical_query, display)
            final = float(text_score) + float(st) + exact_bonus
            reasons = [f"text={text_score:.1f}"] + st_reasons + exact_reasons
            out.append(
                NutritionCandidate(
                    name_key=name_key,
                    display_name=display,
                    text_score=float(text_score),
                    state_score=float(st),
                    final_score=final,
                    reasons=reasons,
                )
            )
        out.sort(key=lambda c: -c.final_score)
        return out

    def _match_state_aware(
        self,
        ni: NormalizedIngredient,
        *,
        include_candidates: bool,
        min_final_score: float = 18.0,
    ) -> dict[str, Any]:
        raw = self._candidate_search(ni.canonical_query, limit=20)
        if not raw:
            raw = self._candidate_search(ni.input_name, limit=20)
        ranked = self._rerank_candidates(ni, raw)
        if ni.input_name.strip().lower() == "milk tea":
            detail = [
                f"{c.display_name!r} final={c.final_score:.1f} text={c.text_score:.1f} "
                f"state_adj={c.state_score:.1f} reasons={c.reasons[:10]}"
                for c in ranked[:15]
            ]
            logger.info(
                "nutrition_milk_tea_debug ingredient=%r state=%r canonical_query=%r "
                "grams=%s candidates=[%s] selected=%r",
                ni.input_name,
                ni.state,
                ni.canonical_query,
                ni.grams,
                " | ".join(detail),
                ranked[0].display_name
                if ranked and ranked[0].final_score >= min_final_score
                else None,
            )
        top_debug = [
            f"{c.display_name[:72]} score={c.final_score:.0f}" for c in ranked[:8]
        ]
        if not ranked or ranked[0].final_score < min_final_score:
            logger.debug(
                "nutrition_match ingredient=%s canonical_query=%s state=%s grams=%s candidates=%s selected=%s",
                ni.input_name,
                ni.canonical_query,
                ni.state,
                ni.grams,
                top_debug,
                None,
            )
            return {}
        best = ranked[0]
        nut = self._data.get(best.name_key)
        if not nut:
            return {}
        scaled = self._scale_row(nut, ni.grams)
        scaled["match"] = best.display_name
        scaled["weight"] = ni.grams
        scaled["state"] = ni.state
        scaled["match_score"] = round(best.final_score, 1)
        if include_candidates:
            scaled["candidates"] = [
                {"name": c.display_name, "score": round(c.final_score, 1)} for c in ranked[:3]
            ]
        cand_str = [f"{c.display_name[:56]} score={c.final_score:.0f}" for c in ranked[:8]]
        logger.debug(
            "nutrition_match ingredient=%s canonical_query=%s state=%s grams=%s candidates=%s selected=%s",
            ni.input_name,
            ni.canonical_query,
            ni.state,
            ni.grams,
            cand_str,
            best.display_name,
        )
        return scaled

    def _scale_row(self, nut: dict[str, Any], weight: Any) -> dict[str, Any]:
        factor = (float(weight) / 100.0) if weight is not None else 0.0
        out: dict[str, Any] = {}
        for k, v in nut.items():
            if k in _SKIP_SCALE_KEYS:
                continue
            try:
                base = float(v)
            except (TypeError, ValueError):
                continue
            out[k] = _round_scaled(k, base * factor)
        return out

    def search(
        self,
        ingredients_weights: dict[str, Any],
        search_type: str = "fuzzy",
        threshold: float = 0.6,
        *,
        include_candidates: bool = False,
    ) -> list[dict]:
        """Per-ingredient match + scaled nutrients (legacy + structured ingredients)."""
        if not self._data or not ingredients_weights:
            return []
        search_type = search_type.lower()
        if search_type not in ("fuzzy", "semantic"):
            search_type = "fuzzy"

        normalized = parse_ingredients_dict(ingredients_weights, self._aliases)
        if not normalized:
            return []

        results: list[dict] = []
        if search_type == "semantic":
            for ni in normalized:
                match = self._semantic_match(ni.canonical_query, threshold)
                if match and match in self._data:
                    nut = self._data[match]
                    disp = str(nut.get("csv_display_name") or match)
                    scaled = self._scale_row(nut, ni.grams)
                    scaled["match"] = disp
                    scaled["weight"] = ni.grams
                    scaled["state"] = ni.state
                    scaled["match_score"] = None
                    results.append({ni.input_name: scaled})
                else:
                    results.append({ni.input_name: {}})
            return results

        for ni in normalized:
            scaled = self._match_state_aware(ni, include_candidates=include_candidates)
            results.append({ni.input_name: scaled})
        return results

    def aggregate_nutrition(self, ingredients_weights: dict[str, Any]) -> dict[str, int] | None:
        full = self.aggregate_nutrition_full(ingredients_weights)
        if not full:
            return None
        return {
            "calories": int(full.get("calories", 0) or 0),
            "proteins": int(full.get("proteins", 0) or 0),
            "fats": int(full.get("fats", 0) or 0),
            "carbohydrates": int(full.get("carbohydrates", 0) or 0),
        }

    def aggregate_nutrition_full(self, ingredients_weights: dict[str, Any]) -> dict[str, float] | None:
        if not self._data or not ingredients_weights:
            return None
        results = self.search(ingredients_weights, search_type="fuzzy")
        totals: dict[str, float] = {}
        skip = _SKIP_SCALE_KEYS | {"match_score", "candidates"}
        for item in results:
            for _ing, data in item.items():
                if not data or not isinstance(data, dict):
                    continue
                for k, v in data.items():
                    if k in skip:
                        continue
                    try:
                        totals[k] = totals.get(k, 0.0) + float(v)
                    except (TypeError, ValueError):
                        continue
        return totals if totals else None

    @property
    def aliases(self) -> FoodAliasIndex:
        return self._aliases

    @property
    def is_available(self) -> bool:
        return bool(self._data)
