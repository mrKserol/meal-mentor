import axios from "axios";

import { authClient } from "./authApi";
import type { IngredientEntry } from "../utils/mealFlow";

const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error("VITE_API_URL is not defined");
}

export async function analyzeMealImageBase64(
  accessToken: string,
  image_base64: string,
): Promise<Record<string, unknown>> {
  const { data } = await authClient.post<Record<string, unknown>>(
    "/users/me/meals/analyze",
    { image_base64 },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return data;
}

export async function analyzeMealText(accessToken: string, text: string): Promise<Record<string, unknown>> {
  const { data } = await authClient.post<Record<string, unknown>>(
    "/users/me/meals/analyze-text",
    { text },
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
): Promise<Record<string, unknown>> {
  const { data } = await authClient.post<Record<string, unknown>>(
    "/users/me/meals/analyze-image-text",
    {
      image_base64,
      text,
      previous_ingredients,
      previous_prediction,
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

export async function saveMyMealToDiary(
  accessToken: string,
  payload: {
    ingredients: Record<string, IngredientEntry>;
    source_type: string;
    telegram_file_id?: string | null;
    prediction?: string | null;
    user_text?: string | null;
    image_base64?: string | null;
    meal_local_date?: string | null;
  },
): Promise<void> {
  await authClient.post("/users/me/meals/save", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
