import { useState } from "react";
import { Navigate } from "react-router-dom";

import { InstallPwaHint } from "../components/InstallPwaHint";
import { useAuth } from "../hooks/useAuth";
import mentorLoginLogo from "../assets/meal-mentor-login-logo.png";

export function LoginPage() {
  const { isAuthenticated } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const telegramClientId = import.meta.env.VITE_TELEGRAM_CLIENT_ID ?? "";
  const telegramRedirectUri = import.meta.env.VITE_TELEGRAM_REDIRECT_URI ?? "";

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const base64Url = (data: ArrayBuffer) =>
    btoa(String.fromCharCode(...new Uint8Array(data)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");

  const randomString = (length: number) => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    const bytes = crypto.getRandomValues(new Uint8Array(length));
    return Array.from(bytes, (b) => chars[b % chars.length]).join("");
  };

  const onTelegramOAuth = async () => {
    if (!telegramClientId || !telegramRedirectUri) {
      setError("Telegram OAuth не настроен. Проверьте VITE_TELEGRAM_CLIENT_ID и VITE_TELEGRAM_REDIRECT_URI.");
      return;
    }
    setError(null);
    const state = randomString(48);
    const codeVerifier = randomString(96);
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(codeVerifier));
    const codeChallenge = base64Url(digest);

    sessionStorage.setItem("telegram_oauth_state", state);
    sessionStorage.setItem("telegram_oauth_code_verifier", codeVerifier);

    const url = new URL("https://oauth.telegram.org/auth");
    url.searchParams.set("client_id", telegramClientId);
    url.searchParams.set("redirect_uri", telegramRedirectUri);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", "openid profile");
    url.searchParams.set("state", state);
    url.searchParams.set("code_challenge", codeChallenge);
    url.searchParams.set("code_challenge_method", "S256");

    window.location.assign(url.toString());
  };

  return (
    <div className="font-body-md text-on-surface min-h-screen flex items-center justify-center p-margin relative bg-surface">
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none -z-10 overflow-hidden opacity-40">
        <div className="absolute top-[-10%] right-[-5%] w-[400px] h-[400px] bg-primary-container/10 rounded-full blur-3xl" />
        <div className="absolute bottom-[-5%] left-[-5%] w-[300px] h-[300px] bg-tertiary-container/10 rounded-full blur-3xl" />
        <div className="absolute top-20 left-20 text-primary-container/20 rotate-12">
          <span className="material-symbols-outlined text-[64px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            eco
          </span>
        </div>
        <div className="absolute bottom-40 right-20 text-secondary-container/30 -rotate-12">
          <span className="material-symbols-outlined text-[48px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            nutrition
          </span>
        </div>
        <div className="absolute top-1/2 left-10 text-primary/10">
          <span className="material-symbols-outlined text-[56px]">monitoring</span>
        </div>
      </div>

      <main className="w-full max-w-[420px] z-10">
        <div className="flex flex-col items-center mb-xl">
          <div className="w-20 h-20 mb-md bg-white rounded-xl shadow-[0_4px_12px_rgba(46,204,113,0.1)] flex items-center justify-center overflow-hidden border border-outline-variant/30">
            <img
              alt="Robot Mentor Logo"
              className="w-14 h-14 object-contain"
              src={mentorLoginLogo}
            />
          </div>
          <h1 className="font-h1 text-h1 text-on-surface mb-xs">Вход в Meal Mentor</h1>
          <p className="font-body-md text-on-surface-variant text-center px-lg">
            Войдите через Telegram — ваш персональный AI-нутрициолог
          </p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/50 p-lg shadow-[0_8px_32px_rgba(0,0,0,0.05)]">
          {error ? <p className="mb-4 text-label-sm text-error">{error}</p> : null}

          <button
            type="button"
            onClick={() => void onTelegramOAuth()}
            className="w-full bg-[#229ED9] hover:opacity-90 text-white py-4 rounded-lg font-h3 text-h3 font-semibold transition shadow-[0_4px_14px_rgba(34,158,217,0.25)]"
          >
            Войти через Telegram
          </button>

          <div className="relative bg-secondary-container/30 p-md rounded-xl border border-secondary-container/50 flex gap-md items-start mt-lg">
            <div className="shrink-0 text-primary-container">
              <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
                smart_toy
              </span>
            </div>
            <p className="font-body-md text-label-sm text-on-secondary-container">
              © 2026 Meal Mentor. Разработка: Алмаз Садыков
            </p>
          </div>
        </div>
      </main>

      <InstallPwaHint />
    </div>
  );
}
