import { authClient } from "./authApi";
import type { MyNutritionTargetEnvelope } from "../types/auth";
import type { DiarySnapshot, WeightMeasurementPeriod, WeightMeasurementsResponse } from "../types/diary";
import type { WebMealsDayResponse } from "../types/mealsDay";

const authHeaders = (token: string) => ({ Authorization: `Bearer ${token}` });

export interface CuratorUserListItem {
  id: number;
  email: string | null;
  username: string | null;
  first_name: string | null;
  role: "user" | "curator" | "admin";
  status: "active" | "blocked";
  subscription_status: string;
  weight_kg: number | null;
  created_at: string | null;
}

export interface CuratorUserProfile {
  id: number;
  first_name: string | null;
  birth_date: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  target_weight_kg: number | null;
  activity_level: string | null;
}

export async function getCuratorUserProfile(token: string, userId: number): Promise<CuratorUserProfile> {
  const { data } = await authClient.get<CuratorUserProfile>(`/curator/users/${userId}/profile`, {
    headers: authHeaders(token),
  });
  return data;
}

export async function getCuratorUsers(token: string): Promise<CuratorUserListItem[]> {
  const { data } = await authClient.get<CuratorUserListItem[]>("/curator/users", {
    headers: authHeaders(token),
  });
  return data;
}

export async function getCuratorUserDiary(token: string, userId: number): Promise<DiarySnapshot> {
  const { data } = await authClient.get<DiarySnapshot>(`/curator/users/${userId}/diary`, {
    headers: authHeaders(token),
  });
  return data;
}

export async function getCuratorUserMealsForDay(
  token: string,
  userId: number,
  dateYmd: string,
): Promise<WebMealsDayResponse> {
  const { data } = await authClient.get<WebMealsDayResponse>(`/curator/users/${userId}/meals/day`, {
    params: { date: dateYmd },
    headers: authHeaders(token),
  });
  return data;
}

export async function getCuratorUserWeightMeasurements(
  token: string,
  userId: number,
  period: WeightMeasurementPeriod,
): Promise<WeightMeasurementsResponse> {
  const { data } = await authClient.get<WeightMeasurementsResponse>(
    `/curator/users/${userId}/measurements`,
    {
      params: { period },
      headers: authHeaders(token),
    },
  );
  return data;
}

export async function getCuratorUserNutritionTarget(
  token: string,
  userId: number,
  dateYmd?: string,
): Promise<MyNutritionTargetEnvelope> {
  const { data } = await authClient.get<MyNutritionTargetEnvelope>(
    `/curator/users/${userId}/nutrition-target`,
    {
      params: dateYmd ? { date: dateYmd } : undefined,
      headers: authHeaders(token),
    },
  );
  return data;
}
