import axios from "axios";

import type {
  AuthResponse,
  LoginPayload,
  MyNutritionTargetEnvelope,
  ProfileUpdatePayload,
  RegisterPayload,
  TelegramCallbackPayload,
  User,
} from "../types/auth";

const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  // Fail fast in development/deploy if env variable was forgotten.
  throw new Error("VITE_API_URL is not defined");
}

/** Axios с baseURL и JSON по умолчанию (не для multipart). */
export const authClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const register = async (payload: RegisterPayload): Promise<AuthResponse> => {
  const response = await authClient.post<AuthResponse>("/auth/register", payload);
  return response.data;
};

export const login = async (payload: LoginPayload): Promise<AuthResponse> => {
  const response = await authClient.post<AuthResponse>("/auth/login", payload);
  return response.data;
};

export const loginWithTelegram = async (payload: TelegramCallbackPayload): Promise<AuthResponse> => {
  const response = await authClient.post<AuthResponse>("/auth/telegram/callback", payload);
  return response.data;
};

export const refresh = async (refreshToken: string): Promise<AuthResponse> => {
  const response = await authClient.post<AuthResponse>("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return response.data;
};

export const logout = async (refreshToken: string): Promise<void> => {
  await authClient.post("/auth/logout", { refresh_token: refreshToken });
};

export const getMe = async (accessToken: string): Promise<User> => {
  const response = await authClient.get<User>("/users/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const me = response.data;
  return { ...me, allergens: me.allergens ?? [] };
};

export const getMyNutritionTarget = async (
  accessToken: string,
  dateYmd?: string,
): Promise<MyNutritionTargetEnvelope> => {
  const response = await authClient.get<MyNutritionTargetEnvelope>("/users/me/nutrition-target", {
    params: dateYmd ? { date: dateYmd } : undefined,
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};

export const updateMyProfile = async (accessToken: string, payload: ProfileUpdatePayload): Promise<User> => {
  const response = await authClient.patch<User>("/users/me/profile", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const me = response.data;
  return { ...me, allergens: me.allergens ?? [] };
};

export interface LabelAnalysisResult {
  text: string;
}

export const analyzeProductLabel = async (
  accessToken: string,
  file: File,
): Promise<LabelAnalysisResult> => {
  const formData = new FormData();
  formData.append("file", file);
  // Не используем authClient: у него default Content-Type: application/json,
  // из‑за этого multipart ломается и FastAPI отвечает "Field required" для file.
  const response = await axios.post<LabelAnalysisResult>(`${API_URL}/users/me/analyze-label`, formData, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};
