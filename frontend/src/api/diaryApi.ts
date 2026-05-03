import { authClient } from "./authApi";
import type { DiarySnapshot } from "../types/diary";
import type { WebMealsDayResponse } from "../types/mealsDay";

export async function getMyDiary(accessToken: string): Promise<DiarySnapshot> {
  const { data } = await authClient.get<DiarySnapshot>("/users/me/diary", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function getMyMealsForDay(accessToken: string, dateYmd: string): Promise<WebMealsDayResponse> {
  const { data } = await authClient.get<WebMealsDayResponse>("/users/me/meals/day", {
    params: { date: dateYmd },
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function deleteMyMeal(accessToken: string, mealId: number): Promise<void> {
  await authClient.delete(`/users/me/meals/${mealId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
