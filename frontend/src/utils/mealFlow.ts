/** Синхронно с backend LOW_CONFIDENCE_THRESHOLD (app/core/config.py). */
export const LOW_CONFIDENCE_THRESHOLD = 0.5;

export type MealNutrition = {
  calories: number;
  proteins: number;
  fats: number;
  carbohydrates: number;
};

/** Legacy: number; structured: { grams, state? } */
export type IngredientEntry = number | string | { grams: number; state?: string };

export type MealAnalyzePayload = {
  status: string;
  ingredients: Record<string, IngredientEntry>;
  confidence: number | null;
  nutrition: MealNutrition | null;
  prediction: string | null;
  error?: string;
};

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
    error: typeof raw.error === "string" ? raw.error : undefined,
  };
}

export function formatRecognitionQuestion(
  ingredients: Record<string, IngredientEntry>,
  prediction?: string | null,
): string {
  const lines: string[] = [];
  const p = typeof prediction === "string" && prediction.trim() ? prediction.trim() : "";

  if (p) {
    lines.push(`Это похоже на: ${p}`);
    lines.push("");
  }

  lines.push("Примерный состав:");
  const keys = Object.keys(ingredients);

  if (keys.length) {
    lines.push(keys.join(" • "));
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
      lines.push(`• ${name}: ${ingredientGramsLabel(ingredients[name])} г`);
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
