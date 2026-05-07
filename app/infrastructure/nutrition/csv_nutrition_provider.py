import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches
from typing import Any

import pandas as pd

from app.core.config import (
    FOOD_ALIASES_PATH,
    NUTRITION_CSV_PATH,
    NUTRITION_ENABLE_SEMANTIC,
    nutrition_debug_matching,
)
from app.infrastructure.nutrition.food_aliases import FoodAliasIndex
from app.infrastructure.nutrition.ingredient_input import (
    is_beer_like_ingredient,
    is_beef_like_ingredient,
    is_porridge_like_grain,
    is_generic_grain_query,
    NormalizedIngredient,
    is_banana_fruit_like,
    is_cottage_cheese_like,
    is_corn_like_ingredient,
    is_grain_like_ingredient,
    is_legume_like_ingredient,
    is_poultry_breast_query,
    is_seafood_like_ingredient,
    is_seed_kernel_query,
    is_tea_drink_query,
    is_tuna_like_ingredient,
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


def safe_float(value: Any) -> float:
    """Convert values to float safely: None/empty/nan -> 0.0."""
    if value is None:
        return 0.0
    if isinstance(value, float) and pd.isna(value):
        return 0.0
    s = str(value).strip().lower()
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


def _parse_cell_to_float(val: Any) -> float:
    return safe_float(val)


def scale_nutrient(value: Any, weight_g: Any) -> float:
    return safe_float(value) * safe_float(weight_g) / 100.0


def aggregate_nutrients(
    ingredients: list[dict[str, Any]],
    nutrition_rows: list[dict[str, Any]] | dict[str, dict[str, Any]],
    field_map: dict[str, str],
) -> dict[str, float]:
    """
    Aggregate per-100g nutrition rows into scaled nutrients.

    `field_map` maps source row keys -> output keys.
    """
    totals: dict[str, float] = {dst: 0.0 for dst in field_map.values()}
    if isinstance(nutrition_rows, dict):
        rows_seq = list(nutrition_rows.values())
    else:
        rows_seq = nutrition_rows
    for idx, row in enumerate(rows_seq):
        if not isinstance(row, dict):
            continue
        ing = ingredients[idx] if idx < len(ingredients) and isinstance(ingredients[idx], dict) else {}
        weight_g = ing.get("grams", ing.get("weight", 0))
        for src, dst in field_map.items():
            totals[dst] = totals.get(dst, 0.0) + scale_nutrient(row.get(src), weight_g)
    return totals


_INT_ROUND_KEYS = frozenset(
    {"calories", "proteins", "fats", "carbohydrates", "sugar_g", "sodium_mg"}
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

    def _series_scaled(self, df: pd.DataFrame, col: str, *, multiplier: float) -> pd.Series:
        return self._series(df, col).map(lambda v: v * multiplier)

    def _series_first_available(self, df: pd.DataFrame, cols: tuple[str, ...]) -> pd.Series:
        for col in cols:
            if col in df.columns:
                return self._series(df, col)
        return pd.Series([0.0] * len(df), index=df.index)

    def _load_data(self) -> None:
        df = pd.read_csv(self._path)
        data = pd.DataFrame(index=df.index)
        data["csv_display_name"] = df["name"].astype(str)
        data["name"] = df["name"].astype(str).str.lower()

        data["calories"] = self._series(df, "calories")
        data["proteins"] = self._series(df, "protein")
        data["fats"] = self._series_first_available(df, ("fat", "total_fat"))
        data["total_fat_g"] = self._series_first_available(df, ("total_fat", "fat"))
        data["carbohydrates"] = self._series(df, "carbohydrate")
        data["fiber_g"] = self._series(df, "fiber")
        data["sugar_g"] = self._series(df, "sugars")
        data["saturated_fat_g"] = self._series(df, "saturated_fat")
        data["saturated_fatty_acids_g"] = self._series_first_available(df, ("saturated_fatty_acids", "saturated_fat"))
        data["monounsaturated_fatty_acids_g"] = self._series(df, "monounsaturated_fatty_acids")
        data["polyunsaturated_fatty_acids_g"] = self._series(df, "polyunsaturated_fatty_acids")
        data["fatty_acids_total_trans_mg"] = self._series(df, "fatty_acids_total_trans")
        data["sodium_mg"] = self._series(df, "sodium")
        data["serving_size_g"] = self._series(df, "serving_size")
        data["cholesterol_mg"] = self._series(df, "cholesterol")
        data["folic_acid_mcg"] = self._series(df, "folic_acid")
        data["calcium_mg"] = self._series(df, "calcium")
        data["magnesium_mg"] = self._series(df, "magnesium")
        data["potassium_mg"] = self._series(df, "potassium")
        data["phosphorus_mg"] = self._series(df, "phosphorus")
        data["iron_mg"] = self._series(df, "iron")
        data["zinc_mg"] = self._series(df, "zinc")
        data["selenium_mcg"] = self._series(df, "selenium")
        data["copper_mg"] = self._series(df, "copper")
        data["manganese_mg"] = self._series(df, "manganese")
        data["vitamin_a_iu"] = self._series(df, "vitamin_a")
        data["vitamin_a_rae_mcg"] = self._series(df, "vitamin_a_rae")
        data["carotene_alpha_mcg"] = self._series(df, "carotene_alpha")
        data["carotene_beta_mcg"] = self._series(df, "carotene_beta")
        data["cryptoxanthin_beta_mcg"] = self._series(df, "cryptoxanthin_beta")
        data["lutein_zeaxanthin_mcg"] = self._series(df, "lutein_zeaxanthin")
        data["lycopene_mcg"] = self._series(df, "lycopene")
        data["vitamin_c_mg"] = self._series(df, "vitamin_c")
        data["vitamin_d_iu"] = self._series(df, "vitamin_d")
        data["vitamin_e_mg"] = self._series(df, "vitamin_e")
        data["tocopherol_alpha_mg"] = self._series(df, "tocopherol_alpha")
        data["vitamin_k_mcg"] = self._series(df, "vitamin_k")
        data["vitamin_b6_mg"] = self._series(df, "vitamin_b6")
        data["vitamin_b12_mcg"] = self._series(df, "vitamin_b12")
        data["folate_mcg"] = self._series(df, "folate")
        data["thiamin_mg"] = self._series(df, "thiamin")
        data["riboflavin_mg"] = self._series(df, "riboflavin")
        data["niacin_mg"] = self._series(df, "niacin")
        data["pantothenic_acid_mg"] = self._series(df, "pantothenic_acid")
        data["choline_mg"] = self._series(df, "choline")
        data["alanine_g"] = self._series(df, "alanine")
        data["arginine_g"] = self._series(df, "arginine")
        data["aspartic_acid_g"] = self._series(df, "aspartic_acid")
        data["cystine_g"] = self._series(df, "cystine")
        data["glutamic_acid_g"] = self._series(df, "glutamic_acid")
        data["glycine_g"] = self._series(df, "glycine")
        data["histidine_g"] = self._series(df, "histidine")
        data["hydroxyproline_g"] = self._series(df, "hydroxyproline")
        data["isoleucine_g"] = self._series(df, "isoleucine")
        data["leucine_g"] = self._series(df, "leucine")
        data["lysine_g"] = self._series(df, "lysine")
        data["methionine_g"] = self._series(df, "methionine")
        data["phenylalanine_g"] = self._series(df, "phenylalanine")
        data["proline_g"] = self._series(df, "proline")
        data["serine_g"] = self._series(df, "serine")
        data["threonine_g"] = self._series(df, "threonine")
        data["tryptophan_g"] = self._series(df, "tryptophan")
        data["tyrosine_g"] = self._series(df, "tyrosine")
        data["valine_g"] = self._series(df, "valine")
        data["fructose_g"] = self._series(df, "fructose")
        data["galactose_g"] = self._series(df, "galactose")
        data["glucose_g"] = self._series(df, "glucose")
        data["lactose_g"] = self._series(df, "lactose")
        data["maltose_g"] = self._series(df, "maltose")
        data["sucrose_g"] = self._series(df, "sucrose")
        data["alcohol_g"] = self._series(df, "alcohol")
        data["ash_g"] = self._series(df, "ash")
        data["caffeine_mg"] = self._series(df, "caffeine")
        data["theobromine_mg"] = self._series(df, "theobromine")
        data["water_g"] = self._series(df, "water")

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
        tuna_like = is_tuna_like_ingredient(ni)
        seafood_like = is_seafood_like_ingredient(ni)
        corn_like = is_corn_like_ingredient(ni)
        beer_q = is_beer_like_ingredient(ni)
        generic_grain_q = is_generic_grain_query(ni)
        beef_q = is_beef_like_ingredient(ni)
        porridge_grain_q = is_porridge_like_grain(ni)
        tea_drink = is_tea_drink_query(ni)
        cottage = is_cottage_cheese_like(ni)
        banana_f = is_banana_fruit_like(ni)
        seed_q = is_seed_kernel_query(ni)
        out: list[NutritionCandidate] = []
        for name_key, text_score in raw_candidates:
            row = self._data.get(name_key) or {}
            display = str(row.get("csv_display_name") or name_key)
            st, st_reasons = state_score(
                ni.state,
                display,
                query=ni.canonical_query,
                ingredient_input=ni.input_name,
                candidate_carbs_per100=float(row.get("carbohydrates") or 0),
                categories=ni.categories,
                is_grain_like=grain,
                is_legume_like=legume,
                is_poultry_breast_query=poultry_breast,
                is_tuna_like=tuna_like,
                seafood_like_q=seafood_like,
                corn_like_q=corn_like,
                beer_q=beer_q,
                generic_grain_query=generic_grain_q,
                beef_q=beef_q,
                porridge_like_grain_q=porridge_grain_q,
                tea_drink_q=tea_drink,
                cottage_cheese_q=cottage,
                banana_fruit_q=banana_f,
                seed_kernel_q=seed_q,
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
        if nutrition_debug_matching():
            detail = [
                f"{c.display_name!r} final={c.final_score:.1f} text={c.text_score:.1f} "
                f"state_score={c.state_score:.1f} reasons={c.reasons[:12]}"
                for c in ranked[:15]
            ]
            logger.info(
                "nutrition_match_debug ingredient=%r state=%r canonical_query=%r "
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
        weight_g = safe_float(weight)
        out: dict[str, Any] = {}
        field_map: dict[str, str] = {}
        for k, v in nut.items():
            if k in _SKIP_SCALE_KEYS:
                continue
            try:
                float(v)
            except (TypeError, ValueError):
                continue
            field_map[k] = k
        scaled = aggregate_nutrients([{"grams": weight_g}], [nut], field_map)
        for k, val in scaled.items():
            out[k] = _round_scaled(k, val)
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
