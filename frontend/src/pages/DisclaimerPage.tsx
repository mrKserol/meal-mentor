import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { DisclaimerTextBlock } from "../components/disclaimer/DisclaimerTextBlock";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";

export function DisclaimerPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  return (
    <AppShell activeNav="home" avatarFallback={avatarFallback} onLogout={handleLogout} showMobileFab={false}>
      <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 lg:py-8">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-green-700">Meal-Mentor</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Дисклеймер</h1>
          </div>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Закрыть
          </button>
        </div>
        <DisclaimerTextBlock />
      </div>
    </AppShell>
  );
}
