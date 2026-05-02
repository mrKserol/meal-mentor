import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import axios from "axios";

import { getMe, login, loginWithTelegram, logout, refresh, updateMyProfile } from "../api/authApi";
import type { AuthResponse, LoginPayload, ProfileUpdatePayload, TelegramCallbackPayload, User } from "../types/auth";

const ACCESS_TOKEN_KEY = "meal_mentor_access_token";
const REFRESH_TOKEN_KEY = "meal_mentor_refresh_token";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  loginWithTelegram: (payload: TelegramCallbackPayload) => Promise<{ isNewUser: boolean; profileCompleted: boolean }>;
  updateProfile: (payload: ProfileUpdatePayload) => Promise<User>;
  logout: () => Promise<void>;
  validateSession: () => Promise<boolean>;
  /** Current access token from storage, if any (after validateSession). */
  getAccessToken: () => string | null;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function saveTokens(tokens: AuthResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

function getTokens(): { accessToken: string | null; refreshToken: string | null } {
  return {
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

function getAccessTokenOrThrow(): string {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (!token) {
    throw new Error("Access token missing");
  }
  return token;
}

function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const validateSession = useCallback(async (): Promise<boolean> => {
    const { accessToken, refreshToken } = getTokens();
    if (!accessToken && !refreshToken) {
      setUser(null);
      return false;
    }

    if (accessToken) {
      try {
        const me = await getMe(accessToken);
        setUser(me);
        return true;
      } catch (error) {
        if (!axios.isAxiosError(error) || error.response?.status !== 401) {
          setUser(null);
          return false;
        }
      }
    }

    if (!refreshToken) {
      clearTokens();
      setUser(null);
      return false;
    }

    try {
      const refreshed = await refresh(refreshToken);
      saveTokens(refreshed);
      const me = await getMe(refreshed.access_token);
      setUser(me);
      return true;
    } catch {
      clearTokens();
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      await validateSession();
      setIsLoading(false);
    };
    void bootstrap();
  }, [validateSession]);

  const loginHandler = useCallback(async (payload: LoginPayload) => {
    const tokens = await login(payload);
    saveTokens(tokens);
    const me = await getMe(tokens.access_token);
    setUser(me);
  }, []);

  const telegramLoginHandler = useCallback(async (payload: TelegramCallbackPayload) => {
    const tokens = await loginWithTelegram(payload);
    saveTokens(tokens);
    const raw = tokens.user ?? (await getMe(tokens.access_token));
    const me: User = { ...raw, allergens: raw.allergens ?? [] };
    setUser(me);
    return {
      isNewUser: Boolean(tokens.is_new_user),
      profileCompleted: Boolean(tokens.profile_completed ?? me.profile_completed),
    };
  }, []);

  const updateProfileHandler = useCallback(
    async (payload: ProfileUpdatePayload) => {
      const sessionOk = await validateSession();
      if (!sessionOk) {
        throw new Error("Session expired");
      }
      const accessToken = getAccessTokenOrThrow();
      const updated = await updateMyProfile(accessToken, payload);
      setUser(updated);
      return updated;
    },
    [validateSession],
  );

  const getAccessToken = useCallback((): string | null => localStorage.getItem(ACCESS_TOKEN_KEY), []);

  const logoutHandler = useCallback(async () => {
    const { refreshToken } = getTokens();
    if (refreshToken) {
      try {
        await logout(refreshToken);
      } catch {
        // We still clear local session even if revoke request fails.
      }
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login: loginHandler,
      loginWithTelegram: telegramLoginHandler,
      updateProfile: updateProfileHandler,
      logout: logoutHandler,
      validateSession,
      getAccessToken,
    }),
    [
      getAccessToken,
      isLoading,
      loginHandler,
      logoutHandler,
      telegramLoginHandler,
      updateProfileHandler,
      user,
      validateSession,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
