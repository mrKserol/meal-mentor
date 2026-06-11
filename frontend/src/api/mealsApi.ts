import axios from "axios";

import { authClient } from "./authApi";
import type { IngredientEntry } from "../utils/mealFlow";

const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error("VITE_API_URL is not defined");
}

type MealAnalyzeContext = {
  comment?: string | null;
  previous_ingredients?: Record<string, IngredientEntry> | null;
  previous_prediction?: string | null;
  correction?: string | null;
  correction_history?: string[];
};

export async function analyzeMealImageBase64(
  accessToken: string,
  image_base64: string,
  context: MealAnalyzeContext = {},
): Promise<Record<string, unknown>> {
  const { data } = await authClient.post<Record<string, unknown>>(
    "/users/me/meals/analyze",
    { image_base64, ...context },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return data;
}

export async function analyzeMealText(
  accessToken: string,
  text: string,
  context: Omit<MealAnalyzeContext, "comment"> = {},
): Promise<Record<string, unknown>> {
  const { data } = await authClient.post<Record<string, unknown>>(
    "/users/me/meals/analyze-text",
    { text, ...context },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return data;
}

export async function analyzeMealImageWithText(
  accessToken: string,
  image_base64: string,
  text: string,
  previous_ingredients?: Record<string, IngredientEntry> | null,
  previous_prediction?: string | null,
  comment?: string | null,
  correction_history?: string[],
): Promise<Record<string, unknown>> {
  const { data } = await authClient.post<Record<string, unknown>>(
    "/users/me/meals/analyze-image-text",
    {
      image_base64,
      text,
      previous_ingredients,
      previous_prediction,
      comment,
      correction_history,
    },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return data;
}

export async function recalculateMealNutrition(
  ingredients: Record<string, IngredientEntry>,
): Promise<Record<string, unknown>> {
  const { data } = await axios.post<Record<string, unknown>>(`${API_URL}/meals/recalculate`, {
    ingredients,
  });
  return data;
}

export type FoodNameResolveResult = {
  status: string;
  input_name: string;
  canonical_name: string | null;
  display_name: string | null;
  language: string | null;
  default_state: string | null;
  category: string | null;
  source: string | null;
  confidence: number | null;
  error?: string;
};

export async function resolveIngredientName(
  accessToken: string,
  payload: { name: string; grams?: number; state?: string | null },
): Promise<FoodNameResolveResult> {
  const { data } = await authClient.post<FoodNameResolveResult>(
    "/users/me/ingredients/resolve",
    payload,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return data;
}

export async function saveMyMealToDiary(
  accessToken: string,
  payload: {
    ingredients: Record<string, IngredientEntry>;
    source_type: string;
    telegram_file_id?: string | null;
    prediction?: string | null;
    prediction_translated?: string | null;
    prediction_language?: string | null;
    user_text?: string | null;
    image_base64?: string | null;
    meal_local_date?: string | null;
    /** Local wall time: YYYY-MM-DDTHH:mm */
    meal_local_datetime?: string | null;
  },
): Promise<void> {
  await authClient.post("/users/me/meals/save", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
