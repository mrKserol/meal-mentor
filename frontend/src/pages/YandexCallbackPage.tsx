import axios from "axios";
import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function YandexCallbackPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { isAuthenticated, loginWithYandex } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      const code = params.get("code");
      const state = params.get("state");
      const savedState = sessionStorage.getItem("yandex_oauth_state");

      if (!code || !state || !savedState) {
        setError("Missing Yandex OAuth parameters.");
        return;
      }

      if (state !== savedState) {
        setError("Invalid Yandex OAuth state.");
        return;
      }

      const redirectUri = import.meta.env.VITE_YANDEX_REDIRECT_URI as string | undefined;
      if (!redirectUri) {
        setError("VITE_YANDEX_REDIRECT_URI не задан.");
        return;
      }

      try {
        const result = await loginWithYandex({
          code,
          state,
          redirect_uri: redirectUri,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        });

        sessionStorage.removeItem("yandex_oauth_state");

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
            `Не удалось подключиться к API для завершения входа через Яндекс. Проверьте VITE_API_URL: ${
              import.meta.env.VITE_API_URL || "не задан"
            }.`,
          );
        } else {
          setError("Yandex login failed.");
        }
      }
    };

    void run();
  }, [loginWithYandex, navigate, params]);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="bg-white border border-outline-variant/40 rounded-xl p-6 max-w-md w-full text-center">
        <h1 className="text-h3 font-h3 text-on-surface mb-2">Yandex OAuth</h1>
        <p className="text-body-md text-on-surface-variant">
          {error ? error : "Завершаем вход через Яндекс..."}
        </p>
      </div>
    </div>
  );
}
