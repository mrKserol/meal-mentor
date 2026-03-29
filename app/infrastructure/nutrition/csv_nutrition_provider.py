import logging
from typing import Any

from difflib import get_close_matches
import pandas as pd

from app.core.config import NUTRITION_CSV_PATH, NUTRITION_ENABLE_SEMANTIC

logger = logging.getLogger(__name__)

# Optional: sentence_transformers for semantic search (downloads from Hugging Face)
try:
    from sentence_transformers import SentenceTransformer, util
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False


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

    def _load_data(self) -> None:
        df = pd.read_csv(self._path)
        data = pd.DataFrame()
        data["name"] = df["name"].str.lower()
        data["calories"] = df["calories"].astype(float)
        data["fats"] = df["total_fat"].str.replace(r"[^\d.]", "", regex=True).astype(float)
        data["proteins"] = df["protein"].str.replace(r"[^\d.]", "", regex=True).astype(float)
        data["carbohydrates"] = df["carbohydrate"].str.replace(r"[^\d.]", "", regex=True).astype(float)
        dataset = data.set_index("name")
        self._data = dataset.to_dict("index")
        self._ingredients = list(self._data.keys())
        # Do NOT load SentenceTransformer here — it blocks on huggingface.co (bad on Railway).

    def _ensure_semantic_model(self) -> bool:
        """Lazy-load embeddings only when semantic search is used and enabled."""
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

    def search(
        self,
        ingredients_weights: dict[str, Any],
        search_type: str = "fuzzy",
        threshold: float = 0.6,
    ) -> list[dict]:
        """Returns list of { ingredient: { match, weight, calories, fats, proteins, carbohydrates } }."""
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
                factor = (float(weight) / 100.0) if weight is not None else 0.0
                scaled = {k: round(nut[k] * factor) for k in nut}
                results.append({
                    ing: {
                        "match": match,
                        "weight": weight,
                        "calories": scaled["calories"],
                        "fats": scaled["fats"],
                        "proteins": scaled["proteins"],
                        "carbohydrates": scaled["carbohydrates"],
                    }
                })
            else:
                results.append({ing: {}})
        return results

    def aggregate_nutrition(self, ingredients_weights: dict[str, Any]) -> dict[str, int] | None:
        """Returns { calories, proteins, fats, carbohydrates } or None if no data."""
        if not self._data or not ingredients_weights:
            return None
        results = self.search(ingredients_weights, search_type="fuzzy")
        total = {"calories": 0, "proteins": 0, "fats": 0, "carbohydrates": 0}
        for item in results:
            for _ing, data in item.items():
                if data and isinstance(data, dict):
                    for k in total:
                        total[k] += data.get(k, 0) or 0
        return total

    @property
    def is_available(self) -> bool:
        return bool(self._data)
