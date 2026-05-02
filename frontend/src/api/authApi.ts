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

const authClient = axios.create({
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
  return response.data;
};

export const getMyNutritionTarget = async (
  accessToken: string,
): Promise<MyNutritionTargetEnvelope> => {
  const response = await authClient.get<MyNutritionTargetEnvelope>("/users/me/nutrition-target", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};

export const updateMyProfile = async (accessToken: string, payload: ProfileUpdatePayload): Promise<User> => {
  const response = await authClient.patch<User>("/users/me/profile", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};
