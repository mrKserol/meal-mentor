import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  Info,
  Scale,
} from "lucide-react";

import { getMyNutritionTarget } from "../api/authApi";
import { getMyDiary } from "../api/diaryApi";
import { MealHistoryDaySection } from "../components/diary/MealHistoryDaySection";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";
import type { DiaryPeriodDay, DiarySnapshot, DiaryWeekDay } from "../types/diary";
import type { NutritionTarget } from "../types/auth";

const MEAL_MENTOR_ACCESS_TOKEN_KEY = "meal_mentor_access_token";

type ChartDay = DiaryWeekDay | DiaryPeriodDay;

function chartDayLabel(d: ChartDay): string {
  if ("weekday_short" in d && typeof d.weekday_short === "string" && d.weekday_short.length > 0) {
    return d.weekday_short;
  }
  const dayOfMonth = Number(d.date.slice(8, 10));
  return Number.isFinite(dayOfMonth) && dayOfMonth > 0 ? String(dayOfMonth) : (d as DiaryPeriodDay).label;
}

function formatFixedRu(n: number, frac = 1): string {
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: frac }).format(n);
}

export function DiaryPage() {
  const navigate = useNavigate();
  const { user, validateSession, logout, getAccessToken } = useAuth();
  const [snapshot, setSnapshot] = useState<DiarySnapshot | null>(null);
  const [nutritionTarget, setNutritionTarget] = useState<NutritionTarget | null>(null);
  const [diaryPhase, setDiaryPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [diaryError, setDiaryError] = useState<string | null>(null);
  const [statsPeriod, setStatsPeriod] = useState<"week" | "month">("week");

  const loadDiary = useCallback(async () => {
    setDiaryPhase("loading");
    setDiaryError(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        navigate("/login", { replace: true });
        return;
      }
      const token = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const [snap, ntEnv] = await Promise.all([getMyDiary(token), getMyNutritionTarget(token)]);
      setSnapshot(snap);
      setNutritionTarget(ntEnv.nutrition_target);
      setDiaryPhase("ready");
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
            : "Не удалось загрузить дневник";
      setDiaryError(message);
      setDiaryPhase("error");
    }
  }, [getAccessToken, navigate, validateSession]);

  useEffect(() => {
    void validateSession();
  }, [validateSession]);

  useEffect(() => {
    if (!user) return;
    void loadDiary();
  }, [user?.id, loadDiary]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  const webDiaryToken = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY) ?? "";

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <p className="text-base text-slate-500">Загрузка дневника...</p>
      </div>
    );
  }

  if (diaryPhase === "error" && diaryError) {
    return (
      <AppShell activeNav="diary" avatarFallback={avatarFallback} onLogout={handleLogout} onMealSaved={loadDiary}>
        <div className="mx-auto flex max-w-lg flex-col items-center gap-4 p-8 text-center">
          <p className="text-lg font-semibold text-slate-900">Не удалось загрузить данные</p>
          <p className="text-slate-600">{diaryError}</p>
          <button
            type="button"
            onClick={() => void loadDiary()}
            className="rounded-lg bg-green-600 px-6 py-3 font-semibold text-white hover:bg-green-700"
          >
            Попробовать снова
          </button>
        </div>
      </AppShell>
    );
  }

  const weightKg = snapshot?.weight.weight_kg ?? user.weight_kg ?? null;
  const deltaWeek = snapshot?.weight.delta_week_kg ?? null;

  const activeStats = statsPeriod === "week" ? snapshot?.week : snapshot?.month;
  const chartDays: ChartDay[] = (activeStats?.days ?? []) as ChartDay[];
  const isMonth = statsPeriod === "month";

  return (
    <AppShell
      activeNav="diary"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      onMealSaved={() => void loadDiary()}
    >
      {() => (
        <div className="mx-auto w-full max-w-7xl overflow-x-hidden p-4 pb-8 lg:p-8">
          <div className="space-y-6">
          {diaryPhase === "loading" && !snapshot ? (
            <p className="text-center text-slate-500">Загружаем данные дневника…</p>
          ) : null}

          <section className="rounded-xl border border-green-100 bg-green-50 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white">
                <Info className="h-5 w-5 text-green-600" aria-hidden />
              </div>
              <div>
                <p className="text-sm font-bold text-green-950">Совет ИИ</p>
                <p className="mt-1 text-sm text-slate-600">Пейте больше воды сегодня!</p>
              </div>
            </div>
          </section>

          <section className="min-w-0">
            <div className="relative min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-50">
                    <BarChart3 className="h-5 w-5 text-green-600" aria-hidden />
                  </div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    {statsPeriod === "week" ? "Статистика за неделю" : "Статистика за месяц"}
                  </h2>
                </div>
                <div className="flex gap-2 text-sm">
                  <button
                    type="button"
                    onClick={() => setStatsPeriod("week")}
                    className={
                      statsPeriod === "week"
                        ? "rounded-full bg-green-100 px-3 py-1 font-medium text-green-700"
                        : "rounded-full px-3 py-1 font-medium text-slate-400 transition hover:bg-slate-100"
                    }
                  >
                    Неделя
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatsPeriod("month")}
                    className={
                      statsPeriod === "month"
                        ? "rounded-full bg-green-100 px-3 py-1 font-medium text-green-700"
                        : "rounded-full px-3 py-1 font-medium text-slate-400 transition hover:bg-slate-100"
                    }
                  >
                    Месяц
                  </button>
                </div>
              </div>

              <div className="w-full min-w-0 overflow-x-auto overscroll-x-contain">
                <div
                  className={[
                    "flex h-48 items-end px-2",
                    isMonth ? "min-w-[620px] justify-between gap-1 md:min-w-0" : "w-full justify-between gap-2",
                  ].join(" ")}
                >
                  {chartDays.map((item) => (
                    <div
                      key={item.date}
                      className={[
                        "flex h-full min-h-0 flex-col items-stretch justify-end px-0.5",
                        isMonth ? "min-w-[18px] flex-1" : "flex-1",
                      ].join(" ")}
                    >
                      <div className="relative flex min-h-[120px] w-full flex-1 items-end rounded-t-lg bg-slate-100">
                        <div
                          className="w-full min-h-[2px] rounded-t-lg bg-green-400 transition-all"
                          style={{ height: item.bar_percent > 0 ? `${item.bar_percent}%` : "2px" }}
                        />
                      </div>
                      <span className="mt-2 block text-center text-xs text-slate-400">{chartDayLabel(item)}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4 border-t border-slate-100 pt-5 text-center md:grid-cols-4">
                <div>
                  <p className="text-xl font-bold text-green-700">{formatFixedRu(activeStats?.avg_calories ?? 0, 0)}</p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Средние ккал</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-orange-600">
                    {formatFixedRu(activeStats?.avg_protein_g ?? 0, 0)} г
                  </p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Белки</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-900">{formatFixedRu(activeStats?.avg_fat_g ?? 0, 0)} г</p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Жиры</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-slate-900">{formatFixedRu(activeStats?.avg_carbs_g ?? 0, 0)} г</p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Углеводы</p>
                </div>
              </div>
            </div>

          </section>

          {webDiaryToken ? (
            <MealHistoryDaySection
              accessToken={webDiaryToken}
              nutritionTarget={nutritionTarget}
              onMealsChanged={() => void loadDiary()}
            />
          ) : null}

          <section className="flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Текущий вес</h2>
                <p className="mt-1 text-3xl font-bold text-green-700">
                  {weightKg != null ? (
                    <>
                      {formatFixedRu(weightKg, 1)} <span className="text-sm font-semibold text-slate-400">кг</span>
                    </>
                  ) : (
                    <span className="text-lg font-semibold text-slate-400">Не указан</span>
                  )}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-green-50">
                <Scale className="h-5 w-5 text-green-600" aria-hidden />
              </div>
            </div>

            <div className="flex flex-1 items-center justify-center py-4">
              <svg className="h-28 w-full" viewBox="0 0 100 40" aria-hidden>
                <path
                  d="M0 35 Q 20 30, 40 32 T 80 15 T 100 10"
                  fill="none"
                  stroke="#15803d"
                  strokeLinecap="round"
                  strokeWidth="2.5"
                />
                <circle cx="100" cy="10" fill="#15803d" r="2.5" />
              </svg>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Прогресс за неделю</span>
                {deltaWeek != null ? (
                  <span className={["font-bold", deltaWeek <= 0 ? "text-green-700" : "text-amber-700"].join(" ")}>
                    {deltaWeek > 0 ? "+" : ""}
                    {formatFixedRu(deltaWeek, 2)} кг
                  </span>
                ) : (
                  <span className="font-medium text-slate-400">Нет взвешиваний</span>
                )}
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-green-400"
                  style={{
                    width:
                      deltaWeek == null
                        ? "0%"
                        : `${Math.min(100, Math.round((Math.abs(deltaWeek) / 2) * 100) || 35)}%`,
                  }}
                />
              </div>
            </div>
          </section>
          </div>
        </div>
      )}
    </AppShell>
  );
}
