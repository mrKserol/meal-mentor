import type { DiaryRecentMeal, DiarySnapshot } from "../types/diary";

export type MealHistoryItem = {
  id: string;
  mealType: string;
  time: string;
  calories: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  fiber_g: number;
  icon: "breakfast" | "lunch" | "snack";
  thumbUrl?: string | null;
  predictionLine: string;
};

function iconFromMealType(mt: string | null): MealHistoryItem["icon"] {
  const m = (mt || "").toLowerCase();
  if (m === "breakfast") return "breakfast";
  if (m === "lunch" || m === "dinner") return "lunch";
  return "snack";
}

export function mealThumbSrcForRecent(m: DiaryRecentMeal): string | undefined {
  if (m.meal_photo_thumb_url) return m.meal_photo_thumb_url;
  const api = import.meta.env.VITE_API_URL as string | undefined;
  if (api && m.meal_photo_thumb) {
    const base = api.replace(/\/$/, "");
    const path = m.meal_photo_thumb.startsWith("/") ? m.meal_photo_thumb : `/${m.meal_photo_thumb}`;
    return `${base}${path}`;
  }
  return undefined;
}

export function mapTodayMealsToHistory(snapshot: DiarySnapshot | null): MealHistoryItem[] {
  if (!snapshot?.today_meals?.length) return [];
  return snapshot.today_meals.map((m) => {
    const pred = typeof m.prediction === "string" && m.prediction.trim() ? m.prediction.trim() : "";
    const predictionLine = pred || "—";
    return {
      id: String(m.id),
      mealType: m.meal_type_label,
      time: m.time_local,
      calories: m.calories,
      protein_g: m.protein_g ?? 0,
      fat_g: m.fat_g ?? 0,
      carbs_g: m.carbs_g ?? 0,
      fiber_g: m.fiber_g ?? 0,
      icon: iconFromMealType(m.meal_type),
      thumbUrl: mealThumbSrcForRecent(m) ?? null,
      predictionLine,
    };
  });
}

export function formatIntRu(n: number): string {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n);
}

/** Grams with ru-RU grouping; fractional part up to `maxFrac` (e.g. fiber 10,3). */
export function formatMacroGramsRu(n: number, maxFrac = 2): string {
  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxFrac,
  }).format(n);
}
