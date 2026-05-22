/** Синхронно с backend LOW_CONFIDENCE_THRESHOLD (app/core/config.py). */
export const LOW_CONFIDENCE_THRESHOLD = 0.5;

export type MealNutrition = {
  calories: number;
  proteins: number;
  fats: number;
  carbohydrates: number;
};

/** Legacy: number; structured: { grams, state?, display fields } */
export type IngredientEntry =
  | number
  | string
  | {
      grams: number;
      state?: string;
      name_translated?: string;
      name_language?: string;
      display_name?: string;
    };

export type MealAnalyzePayload = {
  status: string;
  ingredients: Record<string, IngredientEntry>;
  confidence: number | null;
  nutrition: MealNutrition | null;
  prediction: string | null;
  prediction_translated: string | null;
  prediction_language: string | null;
  error?: string;
};

export function ingredientDisplayName(name: string, entry: IngredientEntry): string {
  if (entry != null && typeof entry === "object" && !Array.isArray(entry)) {
    const e = entry as { name_translated?: unknown; display_name?: unknown };
    if (typeof e.name_translated === "string" && e.name_translated.trim()) {
      return e.name_translated.trim();
    }
    if (typeof e.display_name === "string" && e.display_name.trim()) {
      return e.display_name.trim();
    }
  }
  return name;
}

export function mealDisplayPrediction(state: {
  prediction?: string | null;
  prediction_translated?: string | null;
}): string {
  const tr = state.prediction_translated?.trim();
  if (tr) return tr;
  const base = state.prediction?.trim();
  return base || "";
}

export function setIngredientGrams(
  ingredients: Record<string, IngredientEntry>,
  name: string,
  grams: number,
): Record<string, IngredientEntry> {
  const prev = ingredients[name];
  if (prev != null && typeof prev === "object" && !Array.isArray(prev) && "grams" in prev) {
    return {
      ...ingredients,
      [name]: { ...prev, grams },
    };
  }
  return { ...ingredients, [name]: grams };
}

export function ingredientEntryFromRow(
  grams: number,
  ingredientState?: string | null,
): IngredientEntry {
  const state = (ingredientState || "").trim().toLowerCase();
  if (state && state !== "unknown") {
    return { grams, state };
  }
  return grams;
}

export function ingredientGramsLabel(v: IngredientEntry): string {
  if (v != null && typeof v === "object" && !Array.isArray(v) && "grams" in v) {
    const g = (v as { grams: unknown }).grams;
    return g != null && g !== "" ? String(g) : "";
  }
  if (typeof v === "number" || typeof v === "string") return String(v);
  return "";
}

export function needsUserDescription(ingredients: Record<string, IngredientEntry>, confidence: number | null): boolean {
  if (!ingredients || Object.keys(ingredients).length === 0) return true;
  if (confidence != null && confidence < LOW_CONFIDENCE_THRESHOLD) return true;
  return false;
}

export function parseAnalyzeResponse(raw: Record<string, unknown>): MealAnalyzePayload {
  const status = String(raw.status ?? "error");
  const ing = raw.ingredients;
  const ingredients: Record<string, IngredientEntry> =
    ing && typeof ing === "object" && !Array.isArray(ing) ? (ing as Record<string, IngredientEntry>) : {};
  const confidence = typeof raw.confidence === "number" ? raw.confidence : null;
  const predRaw = raw.prediction;
  const prediction =
    typeof predRaw === "string" && predRaw.trim() ? predRaw.trim() : null;
  const predictionTranslatedRaw = raw.prediction_translated;
  const prediction_translated =
    typeof predictionTranslatedRaw === "string" && predictionTranslatedRaw.trim()
      ? predictionTranslatedRaw.trim()
      : null;
  const predictionLanguageRaw = raw.prediction_language;
  const prediction_language =
    typeof predictionLanguageRaw === "string" && predictionLanguageRaw.trim()
      ? predictionLanguageRaw.trim().toLowerCase()
      : null;
  const nut = raw.nutrition;
  let nutrition: MealNutrition | null = null;
  if (nut && typeof nut === "object" && !Array.isArray(nut)) {
    const n = nut as Record<string, unknown>;
    nutrition = {
      calories: Number(n.calories ?? 0),
      proteins: Number(n.proteins ?? 0),
      fats: Number(n.fats ?? 0),
      carbohydrates: Number(n.carbohydrates ?? 0),
    };
  }
  return {
    status,
    ingredients,
    confidence,
    nutrition,
    prediction,
    prediction_translated,
    prediction_language,
    error: typeof raw.error === "string" ? raw.error : undefined,
  };
}

export function formatRecognitionQuestion(
  ingredients: Record<string, IngredientEntry>,
  prediction?: string | null,
  predictionTranslated?: string | null,
): string {
  const lines: string[] = [];
  const p =
    (typeof predictionTranslated === "string" && predictionTranslated.trim()
      ? predictionTranslated.trim()
      : "") ||
    (typeof prediction === "string" && prediction.trim() ? prediction.trim() : "");

  if (p) {
    lines.push(`Похоже, что это: ${p}`);
    lines.push("");
  }

  lines.push("Примерный состав:");
  const keys = Object.keys(ingredients);

  if (keys.length) {
    lines.push(
      keys.map((name) => ingredientDisplayName(name, ingredients[name])).join(" • "),
    );
  } else {
    lines.push("—");
  }

  lines.push("");
  lines.push("Я верно определил?");

  return lines.join("\n");
}

export function formatMealAnalyzedDetail(
  ingredients: Record<string, IngredientEntry>,
  nutrition: MealNutrition | null,
): string {
  const lines: string[] = ["Состав и вес (г):"];
  const keys = Object.keys(ingredients);
  if (keys.length) {
    for (const name of keys) {
      lines.push(`• ${ingredientDisplayName(name, ingredients[name])}: ${ingredientGramsLabel(ingredients[name])} г`);
    }
  } else {
    lines.push("—");
  }
  if (nutrition) {
    lines.push("");
    lines.push("БЖУ (оценка):");
    lines.push(
      `Калории: ${nutrition.calories} ккал | Б: ${nutrition.proteins} г | Ж: ${nutrition.fats} г | У: ${nutrition.carbohydrates} г`,
    );
  }
  lines.push("");
  lines.push("Записать прием пищи в дневник?");
  return lines.join("\n");
}

export type MealCompositionState = {
  ingredients: Record<string, IngredientEntry>;
  nutrition: MealNutrition | null;
  prediction: string | null;
  prediction_translated?: string | null;
  prediction_language?: string | null;
  image_base64?: string | null;
  image_url?: string | null;
};

export function webMealRowToComposition(meal: {
  id: number;
  prediction: string | null;
  prediction_translated?: string | null;
  prediction_language?: string | null;
  display_prediction?: string | null;
  items: Array<{
    item_name: string | null;
    name_translated?: string | null;
    name_language?: string | null;
    display_name?: string | null;
    estimated_weight_g: number | null;
    ingredient_state?: string | null;
  }>;
  calories: number;
  protein_g?: number;
  fat_g?: number;
  carbs_g?: number;
  meal_photo_large_url?: string | null;
  meal_photo_thumb_url?: string | null;
}): MealCompositionState {
  const ingredients: Record<string, IngredientEntry> = {};
  for (const it of meal.items) {
    const name = (it.item_name || "").trim();
    if (name) {
      ingredients[name] = {
        grams: it.estimated_weight_g ?? 0,
        state: it.ingredient_state || undefined,
        name_translated: it.name_translated || undefined,
        name_language: it.name_language || undefined,
        display_name: it.display_name || undefined,
      };
    }
  }
  return {
    ingredients,
    nutrition: {
      calories: meal.calories,
      proteins: meal.protein_g ?? 0,
      fats: meal.fat_g ?? 0,
      carbohydrates: meal.carbs_g ?? 0,
    },
    prediction: meal.prediction,
    prediction_translated: meal.prediction_translated ?? meal.display_prediction ?? null,
    prediction_language: meal.prediction_language ?? null,
    image_url: meal.meal_photo_large_url || meal.meal_photo_thumb_url || null,
  };
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const r = reader.result as string;
      const i = r.indexOf(",");
      resolve(i >= 0 ? r.slice(i + 1) : r);
    };
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.readAsDataURL(file);
  });
}
