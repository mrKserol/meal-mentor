from typing import Dict, List, Any
import csv
from difflib import get_close_matches
from sentence_transformers import SentenceTransformer, util
import pandas as pd


class IngredientNutritionSearch:
    """
    A class used to search for nutrition information of ingredients using both fuzzy and semantic search methods.
    """

    def __init__(self, dataset_path: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initializes the IngredientNutritionSearch with the dataset path and model name.

        Raises: RuntimeError: If the sentence transformer model fails to load.

        Note: Ingredient names in the dataset and during the search are converted to lowercase for consistent matching.
        """
        self.dataset_path = dataset_path
        self.data = self._load_data()

        self._ingredients = list(self.data.keys())

        if self._ingredients:
            self.model = SentenceTransformer(model_name)
            self._embeddings = self.model.encode(
                self._ingredients,
                convert_to_tensor=True
            )
        else:
            self.model = None
            self._embeddings = None

    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads the ingredient nutrition data from the CSV file.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where keys are ingredient names (in lowercase)
                                       and values are their nutrition data.

            Example:
            {
                'apple': {
                    'calories': 52.0,
                    'fats': 0.2,
                    'proteins': 0.3,
                    'carbohydrates': 13.8
                },
                'banana': {
                    'calories': 89.0,
                    'fats': 0.3,
                    'proteins': 1.1,
                    'carbohydrates': 22.8
                }
            }

        Raises:
            FileNotFoundError: If the dataset file is not found.
            KeyError: If the expected columns are missing from the CSV.
            Exception: For any other errors that occur during file reading.
        """

        data: Dict[str, Dict[str, Any]] = {}

        with open(self.dataset_path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            expected_cols = {"name", "calories", "total_fat", "protein", "carbohydrate"}
            missing = expected_cols - set(reader.fieldnames or [])
            if missing:
                raise KeyError(f"Missing expected columns: {missing}")

            for row in reader:
                ing = (row.get("name") or "").strip().lower()
                if not ing:
                    continue

                try:
                    calories = float(row["calories"])
                    fats = float(row["total_fat"])
                    proteins = float(row["protein"])
                    carbohydrates = float(row["carbohydrate"])
                except (TypeError, ValueError, KeyError):
                    # пропускаем строки с битой/пустой числовой инфой
                    continue

                data[ing] = {
                    "calories": calories,
                    "fats": fats,
                    "proteins": proteins,
                    "carbohydrates": carbohydrates,
                }

        return data


    def _fuzzy_search(self, ingredient_name: str, threshold: float) -> str:
        """
        Searches for the closest matching ingredient name using fuzzy matching based on string similarity.

        The fuzzy search compares the input ingredient name (converted to lowercase) with the list of available
        ingredient names (also in lowercase) and returns the best match based on a similarity score. It uses the
        `get_close_matches` method from the `difflib` module.

        Args:
            ingredient_name (str): The name of the ingredient to search for. The input is converted to lowercase.
            threshold (float): The similarity threshold for fuzzy matching.
                               This value determines how similar the input string must be to return a match.

        Returns:
            str: The closest matching ingredient name if found, otherwise None.

            Example:
                Input: "aple" (misspelled)
                Match found: "apple"
                Result: 'apple'
        """

        def _normalize(self, text: str) -> str:
            text = text.strip().lower()
            if text.endswith("es"):
                return text[:-2]
            if text.endswith("s"):
                return text[:-1]
            return text

        query = ingredient_name.lower().strip()
        matches = get_close_matches(
            query,
            self.data.keys(),
            n=1,
            cutoff=threshold
        )

        if not matches and query.endswith("s"):
            matches = get_close_matches(
                query[:-1],
                self.data.keys(),
                n=1,
                cutoff=threshold
            )
        return matches[0] if matches else None

    def _semantic_search(
        self, ingredient_name: str, threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Searches for the closest matching ingredient name using semantic similarity search.

        The semantic search compares the input ingredient name (converted to lowercase) with the list of
        available ingredient names (also in lowercase) based on semantic meaning rather than string similarity.
        It computes embeddings for both the input and the dataset's ingredient names using a pre-trained sentence
        transformer model, and then calculates cosine similarity between them.

        Args:
            ingredient_name (str): The name of the ingredient to search for. The input is converted to lowercase.
            threshold (float): The similarity threshold for semantic search.
                               This value determines how similar the meaning of the input name must be to return a match.

        Returns:
            str: The closest matching ingredient name if found, otherwise None.

            Example:
                Input: "grn apple" (misspelled or ambiguous)
                Semantic match found: "green apple"
                Result: 'green apple'
        """
        if not self._ingredients or self._embeddings is None:
            return None
        query = ingredient_name.lower().strip()
        try:
            query_emb = self.model.encode(query, convert_to_tensor=True)

        except Exception:
            return None
        cos_scores = util.pytorch_cos_sim(query_emb, self._embeddings)[0]
        best_val, best_idx = cos_scores.max(0)
        score = float(best_val)
        if score < threshold:
            return None
        return self._ingredients[int(best_idx)]

    def search(
        self,
        img_ingredients: Dict[str, Any],
        search_type: str = "fuzzy",
        threshold: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Searches for the nutritional information of a list of ingredients using the specified search type.

        The method supports two search types:
            - "fuzzy": Uses string similarity to find the closest matching ingredient.
            - "semantic": Uses semantic similarity (via embeddings) to find the closest matching ingredient.

        For each ingredient, the method calculates the nutritional values (calories, fats, proteins, carbohydrates)
        based on the provided weight and adds them to the result. If no match is found, an empty dictionary is returned
        for that ingredient.

        Args:
            img_ingredients (Dict[str, Any]): A dict of ingredients and their weights in the format:
                {'ingredient_name': weight_in_grams}.
            search_type (str): The type of search to use, either "fuzzy" or "semantic" (default is "fuzzy").
            threshold (float): The similarity threshold used for matching (default is 0.6).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing ingredient names, their matched values,
                                  and scaled nutritional information based on the provided weight.

            Example:
                Input: {'aple': 150, 'banana': 120}
                Result:
                [
                    {'apple': {'match': 'apple', 'weight': 150, 'calories': 78.0, 'fats': 0.0, 'proteins': 0.0, 'carbohydrates': 21.0}},
                    {'banana': {'match': 'banana', 'weight': 120, 'calories': 107.0, 'fats': 0.4, 'proteins': 1.3, 'carbohydrates': 27.4}}
                ]

        Raises: ValueError: If `search_type` is neither "fuzzy" nor "semantic".

        Note:
        - The nutritional values are scaled proportionally based on the provided weight
            (e.g., 100 grams of a food gives full nutritional values, 50 grams will return half).
        - Rounded values: All nutritional values are rounded to the nearest whole number (0 decimal places).
        """
        search_type = search_type.lower()
        if search_type not in ("fuzzy", "semantic"):
            raise ValueError("search_type must be either 'fuzzy' or 'semantic'")

        results: List[Dict[str, Any]] = []
        for ingredient, weight in img_ingredients.items():
            match: Any = None
            if search_type == "fuzzy":
                match = self._fuzzy_search(ingredient, threshold)
            else:
                match = self._semantic_search(ingredient, threshold)
            if match and match in self.data:
                # Scale nutrients based on weight (per 100g)
                nutrition = self.data[match]
                factor = (float(weight) / 100.0) if weight is not None else 0.0
                scaled = {k: round(nutrition[k] * factor) for k in nutrition}
                results.append({
                    ingredient: {
                        "match": match,
                        "weight": weight,
                        "calories": scaled["calories"],
                        "fats": scaled["fats"],
                        "proteins": scaled["proteins"],
                        "carbohydrates": scaled["carbohydrates"],
                    }
                })
            else:
                results.append({ingredient: {}})
        return results


engine = IngredientNutritionSearch("nutrition.csv")

test_ingredients = {
    "tomatoes": 144,
    "cheese": 125,
    "beef": 133,
    "sausages": 195,
    "pepper": 171,
    "onions": 178,
    "mushrooms": 134,
    "garlic": 133,
    "basil": 191,
    "olives": 166,
}

print("Fuzzy search results:")
fuzzy_results = engine.search(test_ingredients, search_type="fuzzy")
print(fuzzy_results[:1])

for r in fuzzy_results:
    for key, values in r.items():
        print(f"search:{key} // dataset: {values.get('match', 'None')}")

print("Semantic search results:")
semantic_results = engine.search(test_ingredients, search_type="semantic")
print(semantic_results[:1])

for r in semantic_results:
    for key, values in r.items():
        # print(f'search:{key} // dataset: {values["match"]}')
        print(f'search:{key} // dataset: {values.get("match")}')

### Output:
# Fuzzy search results:
# sample: [{'tomatoes': {'match': 'tomato powder', 'weight': 144, 'calories': 435.0, 'fats': 1.0, 'proteins': 19.0, 'carbohydrates': 108.0}}]

# search:tomatoes // dataset: tomato powder
# search:cheese // dataset: cheese, feta
# search:beef // dataset: None
# search:sausages // dataset: blood sausage
# search:pepper // dataset: None
# search:onions // dataset: onions, raw
# search:mushrooms // dataset: mushrooms, raw, white
# search:garlic // dataset: garlic, raw
# search:basil // dataset: None
# search:olives // dataset: jellies

# Semantic search results:
# sample: [{'tomatoes': {'match': 'tomatoes, raw, orange', 'weight': 144, 'calories': 23.0, 'fats': 0.0, 'proteins': 2.0, 'carbohydrates': 5.0}}]

# search:tomatoes // dataset: tomatoes, raw, orange
# search:cheese // dataset: cheese, cheddar
# search:beef // dataset: bologna, beef
# search:sausages // dataset: blood sausage
# search:pepper // dataset: pepper, raw, banana
# search:onions // dataset: onions, raw
# search:mushrooms // dataset: mushrooms, raw, white
# search:garlic // dataset: garlic, raw
# search:basil // dataset: basil, fresh
# search:olives // dataset: olives, canned (small-extra large), ripe
