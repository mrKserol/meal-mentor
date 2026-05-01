import axios from "axios";
import { Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMe, getMyNutritionTarget } from "../api/authApi";
import { HeroBanner } from "../components/dashboard/HeroBanner";
import { MobileBottomNav } from "../components/dashboard/MobileBottomNav";
import { NutritionDiaryCard } from "../components/dashboard/NutritionDiaryCard";
import { ProfileCard } from "../components/dashboard/ProfileCard";
import { SideNav } from "../components/dashboard/SideNav";
import { SubscriptionCard } from "../components/dashboard/SubscriptionCard";
import { TopAppBar } from "../components/dashboard/TopAppBar";
import { useAuth } from "../hooks/useAuth";
import type { NutritionTarget, User } from "../types/auth";

/** Must match ACCESS_TOKEN_KEY in AuthContext.tsx */
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
    const v = profile?.first_name?.trim() || profile?.username?.trim() || "друг";
    return v;
  }, [profile]);

  const heroSubtitle = useMemo(() => {
    if (!nutritionTarget) {
      return "Заполните профиль, чтобы рассчитать дневную цель.";
    }
    return `Сегодня держим ориентир: ${nutritionTarget.target_calories} ккал.`;
  }, [nutritionTarget]);

  const avatarFallback = profile?.first_name?.trim()?.[0]
    ?? profile?.username?.trim()?.[0]
    ?? profile?.email?.trim()?.[0]
    ?? "U";

  if (phase === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-6">
        <p className="text-body-md text-on-surface-variant">Загружаем dashboard...</p>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <p className="font-h3 text-h3 text-on-surface">Не удалось загрузить данные</p>
        <p className="max-w-md text-body-md text-on-surface-variant">{errorMsg}</p>
        <button
          type="button"
          onClick={() => void loadDashboard()}
          className="rounded-lg bg-primary px-6 py-3 font-semibold text-on-primary"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24 text-on-surface antialiased lg:pb-8">
      <TopAppBar avatarFallback={avatarFallback} />
      <SideNav onLogout={handleLogout} />

      <main className="pt-14 lg:ml-64">
        <div className="mx-auto max-w-6xl space-y-8 p-4 lg:p-8">
          <HeroBanner greetingName={greetingName} subtitleLine={heroSubtitle} />

          {!profile?.profile_completed ? (
            <div className="rounded-xl border border-tertiary-container/60 bg-secondary-container/40 px-5 py-4 text-body-md text-on-secondary-container">
              <p>Профиль питания не заполнен полностью.</p>
              <button
                type="button"
                onClick={() => navigate("/onboarding/profile")}
                className="mt-2 font-semibold text-primary underline"
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
      </main>

      <button
        type="button"
        disabled
        title="Скоро"
        className="fixed bottom-24 right-4 z-[45] flex h-14 w-14 cursor-not-allowed items-center justify-center rounded-full bg-primary-container text-on-primary opacity-85 shadow-lg transition-transform lg:hidden"
        aria-label="Записать приём пищи"
      >
        <Plus className="h-7 w-7" aria-hidden strokeWidth={2.5} />
      </button>

      <MobileBottomNav />
    </div>
  );
}
