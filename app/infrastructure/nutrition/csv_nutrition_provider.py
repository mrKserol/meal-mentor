import logging
import re
from typing import Any

from difflib import get_close_matches
import pandas as pd

from app.core.config import NUTRITION_CSV_PATH, NUTRITION_ENABLE_SEMANTIC

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer, util
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False


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


# Per-100g row keys aligned with DB / meal pipeline (proteins → protein_g at persist time)
_INT_ROUND_KEYS = frozenset(
    {"calories", "proteins", "fats", "carbohydrates", "fiber_g", "sugar_g", "sodium_mg"}
)


def _round_scaled(key: str, value: float) -> float | int:
    if key in _INT_ROUND_KEYS:
        return int(round(value))
    return round(value, 3)


class NutritionService:
    """Lookup nutrition per 100g and aggregate for ingredients+weights."""

    def __init__(self, dataset_path: str | None = None):
        self._path = dataset_path or NUTRITION_CSV_PATH
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
        data["name"] = df["name"].astype(str).str.lower()

        # Core macros (per 100 g)
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
        # Prefer RAE (mcg) when present
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

    def _scale_row(self, nut: dict[str, Any], weight: Any) -> dict[str, Any]:
        factor = (float(weight) / 100.0) if weight is not None else 0.0
        out: dict[str, Any] = {}
        for k, v in nut.items():
            if k == "name":
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
    ) -> list[dict]:
        """Per-ingredient match + scaled nutrients (macros + micros)."""
        if not self._data or not ingredients_weights:
            return []
        search_type = search_type.lower()
        if search_type not in ("fuzzy", "semantic"):
            search_type = "fuzzy"
        results = []
        for ing, weight in ingredients_weights.items():
            match = self._fuzzy_match(ing, threshold) if search_type == "fuzzy" else self._semantic_match(ing, threshold)
            if match and match in self._data:
                nut = self._data[match]
                scaled = self._scale_row(nut, weight)
                scaled["match"] = match
                scaled["weight"] = weight
                results.append({ing: scaled})
            else:
                results.append({ing: {}})
        return results

    def aggregate_nutrition(self, ingredients_weights: dict[str, Any]) -> dict[str, int] | None:
        """Legacy totals: calories, proteins, fats, carbohydrates (ints)."""
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
        """Sum all scaled nutrients across ingredients."""
        if not self._data or not ingredients_weights:
            return None
        results = self.search(ingredients_weights, search_type="fuzzy")
        totals: dict[str, float] = {}
        for item in results:
            for _ing, data in item.items():
                if not data or not isinstance(data, dict):
                    continue
                for k, v in data.items():
                    if k in ("match", "weight"):
                        continue
                    try:
                        totals[k] = totals.get(k, 0.0) + float(v)
                    except (TypeError, ValueError):
                        continue
        return totals if totals else None

    @property
    def is_available(self) -> bool:
        return bool(self._data)
