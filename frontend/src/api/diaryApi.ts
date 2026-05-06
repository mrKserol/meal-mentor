import { authClient } from "./authApi";
import type {
  CreateWeightMeasurementPayload,
  DiarySnapshot,
  WeightMeasurementPeriod,
  WeightMeasurementPoint,
  WeightMeasurementsResponse,
} from "../types/diary";
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

export async function getMyWeightMeasurements(
  accessToken: string,
  period: WeightMeasurementPeriod,
): Promise<WeightMeasurementsResponse> {
  const { data } = await authClient.get<WeightMeasurementsResponse>("/users/me/measurements", {
    params: { period },
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function addMyWeightMeasurement(
  accessToken: string,
  payload: CreateWeightMeasurementPayload,
): Promise<WeightMeasurementPoint> {
  const { data } = await authClient.post<WeightMeasurementPoint>("/users/me/measurements", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}
