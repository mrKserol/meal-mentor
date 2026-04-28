import axios from "axios";

import type { AuthLoginPayload, AuthRegisterPayload, AuthTokenPair, MeUser } from "../types/auth";

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

export const registerRequest = async (payload: AuthRegisterPayload): Promise<AuthTokenPair> => {
  const response = await authClient.post<AuthTokenPair>("/auth/register", {
    email: payload.email,
    username: payload.full_name,
    password: payload.password,
  });
  return response.data;
};

export const loginRequest = async (payload: AuthLoginPayload): Promise<AuthTokenPair> => {
  const response = await authClient.post<AuthTokenPair>("/auth/login", payload);
  return response.data;
};

export const refreshRequest = async (refreshToken: string): Promise<AuthTokenPair> => {
  const response = await authClient.post<AuthTokenPair>("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return response.data;
};

export const logoutRequest = async (refreshToken: string): Promise<void> => {
  await authClient.post("/auth/logout", { refresh_token: refreshToken });
};

export const meRequest = async (accessToken: string): Promise<MeUser> => {
  const response = await authClient.get<MeUser>("/users/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};
