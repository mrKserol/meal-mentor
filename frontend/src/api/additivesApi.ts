import { authClient } from "./authApi";
import type {
  AdditiveAnalyzeResponse,
  AdditiveCreatePayload,
  AdditiveIntakeCreatePayload,
  AdditiveIntakeListResponse,
  AdditiveIntakeItem,
  AdditiveItem,
  AdditiveListResponse,
  AdditiveUpdatePayload,
  NutrientField,
  WaterIntakeCreatePayload,
} from "../types/additives";

export async function getAdditiveNutrientFields(token: string): Promise<NutrientField[]> {
  const { data } = await authClient.get<NutrientField[]>("/users/me/additives/nutrient-fields", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function analyzeAdditiveImageBase64(
  token: string,
  imageBase64: string,
): Promise<AdditiveAnalyzeResponse> {
  const { data } = await authClient.post<AdditiveAnalyzeResponse>(
    "/users/me/additives/analyze",
    { image_base64: imageBase64 },
    { headers: { Authorization: `Bearer ${token}` } },
  );
  return data;
}

export async function createAdditive(token: string, payload: AdditiveCreatePayload): Promise<AdditiveItem> {
  const { data } = await authClient.post<AdditiveItem>("/users/me/additives", payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function listAdditives(token: string): Promise<AdditiveListResponse> {
  const { data } = await authClient.get<AdditiveListResponse>("/users/me/additives", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function getAdditive(token: string, id: number): Promise<AdditiveItem> {
  const { data } = await authClient.get<AdditiveItem>(`/users/me/additives/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function updateAdditive(
  token: string,
  id: number,
  payload: AdditiveUpdatePayload,
): Promise<AdditiveItem> {
  const { data } = await authClient.patch<AdditiveItem>(`/users/me/additives/${id}`, payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function deleteAdditive(token: string, id: number): Promise<void> {
  await authClient.delete(`/users/me/additives/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function recordAdditiveIntake(
  token: string,
  payload: AdditiveIntakeCreatePayload,
): Promise<AdditiveIntakeItem> {
  const { data } = await authClient.post<AdditiveIntakeItem>("/users/me/additive-intakes", payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function getAdditiveIntakesForDay(
  token: string,
  dateYmd: string,
): Promise<AdditiveIntakeListResponse> {
  const { data } = await authClient.get<AdditiveIntakeListResponse>("/users/me/additive-intakes/day", {
    params: { date: dateYmd },
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function deleteAdditiveIntake(token: string, intakeId: number): Promise<void> {
  await authClient.delete(`/users/me/additive-intakes/${intakeId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function recordWaterIntake(
  token: string,
  payload: WaterIntakeCreatePayload,
): Promise<AdditiveIntakeItem> {
  const { data } = await authClient.post<AdditiveIntakeItem>("/users/me/water-intakes", payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}
