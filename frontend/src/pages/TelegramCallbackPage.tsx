import axios from "axios";
import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function TelegramCallbackPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { isAuthenticated, loginWithTelegram } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      const code = params.get("code");
      const state = params.get("state");
      const savedState = sessionStorage.getItem("telegram_oauth_state");
      const codeVerifier = sessionStorage.getItem("telegram_oauth_code_verifier");

      if (!code || !state || !savedState || !codeVerifier) {
        setError("Missing Telegram OAuth parameters.");
        return;
      }
      if (state !== savedState) {
        setError("Invalid Telegram OAuth state.");
        return;
      }

      try {
        const result = await loginWithTelegram({
          code,
          state,
          code_verifier: codeVerifier,
          redirect_uri: import.meta.env.VITE_TELEGRAM_REDIRECT_URI,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        });
        sessionStorage.removeItem("telegram_oauth_state");
        sessionStorage.removeItem("telegram_oauth_code_verifier");
        if (result.isNewUser || !result.profileCompleted) {
          navigate("/onboarding/profile", { replace: true });
        } else {
          navigate("/dashboard", { replace: true });
        }
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          const detail = requestError.response?.data?.detail;
          if (detail) {
            setError(String(detail));
            return;
          }
          setError(
            `Не удалось подключиться к API для завершения Telegram OAuth. Проверьте VITE_API_URL: ${
              import.meta.env.VITE_API_URL || "не задан"
            }.`,
          );
        } else {
          setError("Telegram login failed.");
        }
      }
    };

    void run();
  }, [loginWithTelegram, navigate, params]);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="bg-white border border-outline-variant/40 rounded-xl p-6 max-w-md w-full text-center">
        <h1 className="text-h3 font-h3 text-on-surface mb-2">Telegram OAuth</h1>
        <p className="text-body-md text-on-surface-variant">
          {error ? error : "Завершаем вход через Telegram..."}
        </p>
      </div>
    </div>
  );
}
