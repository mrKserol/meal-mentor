import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import axios from "axios";

import { loginRequest, logoutRequest, meRequest, refreshRequest } from "../api/authApi";
import type { AuthLoginPayload, AuthTokenPair, MeUser } from "../types/auth";

const ACCESS_TOKEN_KEY = "meal_mentor_access_token";
const REFRESH_TOKEN_KEY = "meal_mentor_refresh_token";

interface AuthContextValue {
  user: MeUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: AuthLoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  validateSession: () => Promise<boolean>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function saveTokens(tokens: AuthTokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

function getTokens(): { accessToken: string | null; refreshToken: string | null } {
  return {
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const validateSession = useCallback(async (): Promise<boolean> => {
    const { accessToken, refreshToken } = getTokens();
    if (!accessToken && !refreshToken) {
      setUser(null);
      return false;
    }

    if (accessToken) {
      try {
        const me = await meRequest(accessToken);
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
      const refreshed = await refreshRequest(refreshToken);
      saveTokens(refreshed);
      const me = await meRequest(refreshed.access_token);
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

  const login = useCallback(async (payload: AuthLoginPayload) => {
    const tokens = await loginRequest(payload);
    saveTokens(tokens);
    const me = await meRequest(tokens.access_token);
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    const { refreshToken } = getTokens();
    if (refreshToken) {
      try {
        await logoutRequest(refreshToken);
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
      login,
      logout,
      validateSession,
    }),
    [isLoading, login, logout, user, validateSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
