import axios from "axios";

import { authClient } from "./authApi";
import type { IngredientEntry } from "../utils/mealFlow";

const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error("VITE_API_URL is not defined");
}

export async function analyzeMealImageBase64(image_base64: string): Promise<Record<string, unknown>> {
  const { data } = await axios.post<Record<string, unknown>>(`${API_URL}/meals/analyze`, { image_base64 });
  return data;
}

export async function analyzeMealText(text: string): Promise<Record<string, unknown>> {
  const { data } = await axios.post<Record<string, unknown>>(`${API_URL}/meals/analyze-text`, { text });
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
  },
): Promise<void> {
  await authClient.post("/users/me/meals/save", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
