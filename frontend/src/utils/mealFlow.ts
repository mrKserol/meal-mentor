/** Синхронно с backend LOW_CONFIDENCE_THRESHOLD (app/core/config.py). */
export const LOW_CONFIDENCE_THRESHOLD = 0.5;

export type MealNutrition = {
  calories: number;
  proteins: number;
  fats: number;
  carbohydrates: number;
};

export type MealAnalyzePayload = {
  status: string;
  ingredients: Record<string, string | number>;
  confidence: number | null;
  nutrition: MealNutrition | null;
  error?: string;
};

export function needsUserDescription(ingredients: Record<string, string | number>, confidence: number | null): boolean {
  if (!ingredients || Object.keys(ingredients).length === 0) return true;
  if (confidence != null && confidence < LOW_CONFIDENCE_THRESHOLD) return true;
  return false;
}

export function parseAnalyzeResponse(raw: Record<string, unknown>): MealAnalyzePayload {
  const status = String(raw.status ?? "error");
  const ing = raw.ingredients;
  const ingredients: Record<string, string | number> =
    ing && typeof ing === "object" && !Array.isArray(ing) ? (ing as Record<string, string | number>) : {};
  const confidence = typeof raw.confidence === "number" ? raw.confidence : null;
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
    error: typeof raw.error === "string" ? raw.error : undefined,
  };
}

export function formatRecognitionQuestion(ingredients: Record<string, string | number>): string {
  const keys = Object.keys(ingredients);
  if (keys.length === 0) {
    return "Я не смог выделить ингредиенты. Опиши блюдо текстом или попробуй другое фото.";
  }
  const parts = keys.map((name) => `${name} (${ingredients[name]} г)`);
  let tail: string;
  if (parts.length === 1) tail = parts[0];
  else if (parts.length === 2) tail = `${parts[0]} и ${parts[1]}`;
  else tail = `${parts.slice(0, -1).join(", ")} и ${parts[parts.length - 1]}`;
  return `Это похоже на: ${tail}.\n\nЯ верно определил?`;
}

export function formatMealAnalyzedDetail(
  ingredients: Record<string, string | number>,
  nutrition: MealNutrition | null,
): string {
  const lines: string[] = ["Состав и вес (г):"];
  const keys = Object.keys(ingredients);
  if (keys.length) {
    for (const name of keys) {
      lines.push(`• ${name}: ${ingredients[name]} г`);
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
