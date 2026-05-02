import axios from "axios";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMe, getMyNutritionTarget } from "../api/authApi";
import { HeroBanner } from "../components/dashboard/HeroBanner";
import { NutritionDiaryCard } from "../components/dashboard/NutritionDiaryCard";
import { ProfileCard } from "../components/dashboard/ProfileCard";
import { SubscriptionCard } from "../components/dashboard/SubscriptionCard";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";
import type { NutritionTarget, User } from "../types/auth";

const MEAL_MENTOR_ACCESS_TOKEN_KEY = "meal_mentor_access_token";

export function DashboardPage() {
  const navigate = useNavigate();
  const { validateSession, logout } = useAuth();
  const [phase, setPhase] = useState<"loading" | "error" | "ready">("loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [profile, setProfile] = useState<User | null>(null);
  const [nutritionTarget, setNutritionTarget] = useState<NutritionTarget | null>(null);

  const loadDashboard = useCallback(async () => {
    setPhase("loading");
    setErrorMsg(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        navigate("/login", { replace: true });
        return;
      }
      const token = localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const me = await getMe(token);
      setProfile(me);
      let nt: NutritionTarget | null = me.nutrition_target ?? null;
      if (nt === null || nt === undefined) {
        const envelope = await getMyNutritionTarget(token);
        nt = envelope.nutrition_target;
      }
      setNutritionTarget(nt);
      setPhase("ready");
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 401) {
        navigate("/login", { replace: true });
        return;
      }
      const message =
        axios.isAxiosError(e) && e.response?.data?.detail != null
          ? String(e.response.data.detail)
          : e instanceof Error
            ? e.message
            : "Не удалось загрузить данные";
      setErrorMsg(message);
      setPhase("error");
    }
  }, [navigate, validateSession]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const greetingName = useMemo(() => {
    return profile?.first_name?.trim() || profile?.username?.trim() || "друг";
  }, [profile]);

  const heroSubtitle = useMemo(() => {
    if (!nutritionTarget) {
      return "Заполните профиль, чтобы рассчитать дневную цель.";
    }
    return `Сегодня держим ориентир: ${nutritionTarget.target_calories} ккал.`;
  }, [nutritionTarget]);

  const avatarFallback =
    profile?.first_name?.trim()?.[0] ??
    profile?.username?.trim()?.[0] ??
    profile?.email?.trim()?.[0] ??
    "U";

  if (phase === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <p className="text-base text-slate-500">Загружаем dashboard...</p>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-6 text-center">
        <p className="text-xl font-semibold text-slate-900">Не удалось загрузить данные</p>
        <p className="max-w-md text-base text-slate-600">{errorMsg}</p>
        <button
          type="button"
          onClick={() => void loadDashboard()}
          className="rounded-lg bg-green-600 px-6 py-3 font-semibold text-white hover:bg-green-700"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <AppShell activeNav="home" avatarFallback={avatarFallback} onLogout={handleLogout}>
      <div className="mx-auto max-w-6xl space-y-8 p-4 lg:p-8">
        <HeroBanner greetingName={greetingName} subtitleLine={heroSubtitle} />

        {!profile?.profile_completed ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-base text-amber-950">
            <p>Профиль питания не заполнен полностью.</p>
            <button
              type="button"
              onClick={() => navigate("/onboarding/profile")}
              className="mt-2 font-semibold text-green-700 underline hover:text-green-800"
            >
              Заполнить профиль
            </button>
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="space-y-8 lg:col-span-2">
            <NutritionDiaryCard nutritionTarget={nutritionTarget} />
          </div>
          <div className="flex flex-col gap-8">
            <ProfileCard user={profile} />
            <SubscriptionCard
              subscriptionStatus={profile?.subscription_status}
              onUpgradeClick={() => {
                /* платёжный поток будет подключён отдельно */
              }}
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
