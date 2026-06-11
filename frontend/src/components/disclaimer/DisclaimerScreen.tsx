import axios from "axios";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { acceptConsent } from "../../api/consentsApi";
import { useAuth } from "../../hooks/useAuth";
import { DISCLAIMER_CONFIRMATION_TEXT, DISCLAIMER_TITLE } from "./disclaimerText";
import { DisclaimerTextBlock } from "./DisclaimerTextBlock";

interface DisclaimerScreenProps {
  currentVersion: string;
  onAccepted?: () => void;
}

export function DisclaimerScreen({ currentVersion, onAccepted }: DisclaimerScreenProps) {
  const navigate = useNavigate();
  const { getAccessToken, logout } = useAuth();
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAccept = async () => {
    if (!checked || loading) return;

    const accessToken = getAccessToken();
    if (!accessToken) {
      navigate("/login", { replace: true });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await acceptConsent(accessToken, {
        consent_type: "disclaimer",
        consent_version: currentVersion,
      });
      onAccepted?.();
      navigate("/onboarding/profile", { replace: true });
    } catch (requestError) {
      if (axios.isAxiosError(requestError) && requestError.response?.data?.detail) {
        setError(String(requestError.response.data.detail));
      } else {
        setError("Не удалось сохранить согласие. Попробуйте ещё раз.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 text-slate-900 sm:px-6">
      <main className="mx-auto flex h-[calc(100vh-3rem)] max-w-3xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-slate-50 shadow-xl shadow-slate-900/10">
        <div className="shrink-0 border-b border-slate-200 bg-white px-5 py-4 sm:px-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-green-700">Meal-Mentor</p>
          <h1 className="mt-1 text-lg font-bold tracking-tight text-slate-950 sm:text-xl">{DISCLAIMER_TITLE}</h1>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          <DisclaimerTextBlock />
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-white px-5 py-4 sm:px-6">
          <label className="flex cursor-pointer items-start gap-3 rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
            <input
              type="checkbox"
              checked={checked}
              onChange={(event) => setChecked(event.target.checked)}
              className="mt-1 h-5 w-5 shrink-0 rounded border-slate-300 text-green-600 focus:ring-green-500"
            />
            <span>{DISCLAIMER_CONFIRMATION_TEXT}</span>
          </label>

          {error ? <p className="mt-3 text-sm font-medium text-red-600">{error}</p> : null}

          <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={() => void handleCancel()}
              className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              disabled={loading}
            >
              Отмена
            </button>
            <button
              type="button"
              onClick={() => void handleAccept()}
              disabled={!checked || loading}
              className="rounded-xl bg-green-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Сохраняем..." : "Регистрация"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
