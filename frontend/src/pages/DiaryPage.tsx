import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Apple,
  BarChart3,
  Beef,
  ChevronRight,
  CirclePlus,
  Coffee,
  EggFried,
  Flame,
  Info,
  Salad,
  Scale,
  Target,
  Wheat,
} from "lucide-react";

import { getMyNutritionTarget } from "../api/authApi";
import { getMyDiary } from "../api/diaryApi";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";
import type { DiaryPeriodDay, DiarySnapshot, DiaryWeekDay } from "../types/diary";
import type { NutritionTarget } from "../types/auth";

type MealHistoryItem = {
  id: string;
  mealType: string;
  time: string;
  calories: number;
  icon: "breakfast" | "lunch" | "snack";
  thumbUrl?: string | null;
  predictionLine: string;
  composition: string;
};

type GoalIconKind = "calories" | "protein" | "fat" | "carbs";

type DailyGoalItem = {
  id: string;
  label: string;
  current: string;
  target: string;
  percent: number;
  tone: "green" | "orange" | "slate";
  icon: GoalIconKind;
};

const MEAL_MENTOR_ACCESS_TOKEN_KEY = "meal_mentor_access_token";

type ChartDay = DiaryWeekDay | DiaryPeriodDay;

function chartDayLabel(d: ChartDay): string {
  if ("weekday_short" in d && typeof d.weekday_short === "string" && d.weekday_short.length > 0) {
    return d.weekday_short;
  }
  return (d as DiaryPeriodDay).label;
}

function formatIntRu(n: number): string {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n);
}

function formatFixedRu(n: number, frac = 1): string {
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: frac }).format(n);
}

function getTodayRu(): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
  }).format(new Date());
}

function iconFromMealType(mt: string | null): MealHistoryItem["icon"] {
  const m = (mt || "").toLowerCase();
  if (m === "breakfast") return "breakfast";
  if (m === "lunch" || m === "dinner") return "lunch";
  return "snack";
}

function pctCurrentTarget(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.min(100, Math.round((100 * current) / target));
}

function goalToneFromPercent(percent: number): DailyGoalItem["tone"] {
  if (percent >= 100) return "orange";
  if (percent >= 60) return "green";
  return "slate";
}

function buildDailyGoals(nt: NutritionTarget | null, today: DiarySnapshot["today"]): DailyGoalItem[] {
  if (!nt) return [];
  const c = pctCurrentTarget(today.calories, nt.target_calories);
  const p = pctCurrentTarget(today.protein_g, nt.target_protein_g);
  const f = pctCurrentTarget(today.fat_g, nt.target_fat_g);
  const cb = pctCurrentTarget(today.carbs_g, nt.target_carbs_g);
  return [
    {
      id: "calories",
      label: "Калории",
      current: formatIntRu(today.calories),
      target: `${formatIntRu(nt.target_calories)} kcal`,
      percent: c,
      tone: goalToneFromPercent(c),
      icon: "calories",
    },
    {
      id: "protein",
      label: "Белки",
      current: formatIntRu(today.protein_g),
      target: `${formatIntRu(nt.target_protein_g)} г`,
      percent: p,
      tone: goalToneFromPercent(p),
      icon: "protein",
    },
    {
      id: "fat",
      label: "Жиры",
      current: formatIntRu(today.fat_g),
      target: `${formatIntRu(nt.target_fat_g)} г`,
      percent: f,
      tone: goalToneFromPercent(f),
      icon: "fat",
    },
    {
      id: "carbs",
      label: "Углеводы",
      current: formatIntRu(today.carbs_g),
      target: `${formatIntRu(nt.target_carbs_g)} г`,
      percent: cb,
      tone: goalToneFromPercent(cb),
      icon: "carbs",
    },
  ];
}

function mealThumbSrc(m: DiarySnapshot["recent_meals"][number]): string | undefined {
  if (m.meal_photo_thumb_url) return m.meal_photo_thumb_url;
  const api = import.meta.env.VITE_API_URL as string | undefined;
  if (api && m.meal_photo_thumb) {
    const base = api.replace(/\/$/, "");
    const path = m.meal_photo_thumb.startsWith("/") ? m.meal_photo_thumb : `/${m.meal_photo_thumb}`;
    return `${base}${path}`;
  }
  return undefined;
}

function mapRecentToHistory(snapshot: DiarySnapshot | null): MealHistoryItem[] {
  if (!snapshot?.recent_meals?.length) return [];
  return snapshot.recent_meals.map((m) => {
    const pred = typeof m.prediction === "string" && m.prediction.trim() ? m.prediction.trim() : "";
    const predictionLine = pred || "—";
    const composition = (m.composition && m.composition.trim()) || "—";
    return {
      id: String(m.id),
      mealType: m.meal_type_label,
      time: m.time_local,
      calories: m.calories,
      icon: iconFromMealType(m.meal_type),
      thumbUrl: mealThumbSrc(m) ?? null,
      predictionLine,
      composition,
    };
  });
}

function getMealIcon(icon: MealHistoryItem["icon"]) {
  if (icon === "breakfast") return Coffee;
  if (icon === "lunch") return Salad;
  return Apple;
}

function getGoalIcon(icon: GoalIconKind) {
  if (icon === "calories") return Flame;
  if (icon === "protein") return Beef;
  if (icon === "fat") return EggFried;
  return Wheat;
}

function goalStrokeClass(tone: DailyGoalItem["tone"]): string {
  if (tone === "green") return "stroke-green-600";
  if (tone === "orange") return "stroke-orange-500";
  return "stroke-slate-700";
}

function goalIconClass(tone: DailyGoalItem["tone"]): string {
  if (tone === "green") return "text-green-600";
  if (tone === "orange") return "text-orange-500";
  return "text-slate-700";
}

function MealIconCard({ icon }: { icon: MealHistoryItem["icon"] }) {
  const Icon = getMealIcon(icon);

  return (
    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
      <Icon className="h-7 w-7" aria-hidden />
    </div>
  );
}

function DailyGoalProgress({ item }: { item: DailyGoalItem }) {
  const Icon = getGoalIcon(item.icon);
  const strokeClass = goalStrokeClass(item.tone);
  const iconClass = goalIconClass(item.tone);

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-14 w-14 shrink-0">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36" aria-hidden>
          <circle className="stroke-slate-100" cx="18" cy="18" fill="none" r="16" strokeWidth="3" />
          <circle
            className={strokeClass}
            cx="18"
            cy="18"
            fill="none"
            r="16"
            strokeDasharray={`${item.percent}, 100`}
            strokeLinecap="round"
            strokeWidth="3"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <Icon className={`h-5 w-5 ${iconClass}`} aria-hidden />
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-slate-900">{item.label}</p>
        <p className="text-xs text-slate-500">
          {item.current} / {item.target}
        </p>
      </div>
      <span className="shrink-0 text-sm font-bold text-slate-700">{item.percent}%</span>
    </div>
  );
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

  const mealHistory = useMemo(() => mapRecentToHistory(snapshot), [snapshot]);

  const dailyGoals = useMemo(() => {
    if (!snapshot || !nutritionTarget) return [];
    return buildDailyGoals(nutritionTarget, snapshot.today);
  }, [snapshot, nutritionTarget]);

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
  const periodLength = statsPeriod === "week" ? 7 : (snapshot?.month.days.length ?? 0);
  const chartDays: ChartDay[] = (activeStats?.days ?? []) as ChartDay[];
  const isMonth = statsPeriod === "month";
  const showAvgHint =
    Boolean(activeStats) &&
    periodLength > 0 &&
    activeStats!.days_with_data > 0 &&
    activeStats!.days_with_data < periodLength;

  return (
    <AppShell
      activeNav="diary"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      onMealSaved={() => void loadDiary()}
    >
      {({ openAddMeal }) => (
        <div className="mx-auto max-w-7xl space-y-6 p-4 pb-8 lg:p-8">
          <section className="flex flex-col justify-between gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:flex-row md:items-center">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">Обзор питания</h1>
              <p className="mt-2 text-slate-500">
                Отслеживайте свой прогресс и записывайте приёмы пищи за {getTodayRu()}
              </p>
            </div>
            <button
              type="button"
              onClick={() => openAddMeal()}
              className="flex items-center justify-center gap-2 rounded-lg bg-green-500 px-6 py-3 font-semibold text-green-950 shadow-sm transition hover:bg-green-400 active:scale-[0.98]"
            >
              <CirclePlus className="h-5 w-5" aria-hidden />
              Добавить прием пищи
            </button>
          </section>

          {diaryPhase === "loading" && !snapshot ? (
            <p className="text-center text-slate-500">Загружаем данные дневника…</p>
          ) : null}

          <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:col-span-2">
              <div className="mb-6 flex items-center justify-between gap-4">
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

              <div
                className={[
                  "flex h-48 w-full items-end px-2",
                  isMonth ? "justify-between gap-1 overflow-x-auto" : "justify-between gap-2",
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

              {showAvgHint ? (
                <p className="mt-2 text-center text-xs text-slate-400">
                  Средние посчитаны за {activeStats!.days_with_data}{" "}
                  {activeStats!.days_with_data === 1
                    ? "день"
                    : activeStats!.days_with_data >= 2 && activeStats!.days_with_data <= 4
                      ? "дня"
                      : "дней"}{" "}
                  с записями,{" "}
                  {statsPeriod === "week"
                    ? "а не за все 7 дней интервала"
                    : "а не за все 30 дней интервала"}
                </p>
              ) : null}

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

            <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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
                  <span
                    className={[
                      "font-bold",
                      deltaWeek <= 0 ? "text-green-700" : "text-amber-700",
                    ].join(" ")}
                  >
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
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6 md:grid-cols-12">
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm md:col-span-8">
              <div className="flex items-center justify-between border-b border-slate-100 p-6">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">История приёмов пищи</h2>
                  <p className="mt-1 text-sm text-slate-500">Последние 3 приёма пищи</p>
                </div>
                <button
                  type="button"
                  onClick={() => openAddMeal()}
                  className="flex items-center gap-1 text-sm font-bold text-green-700 transition hover:text-green-800"
                >
                  Добавить
                  <ChevronRight className="h-4 w-4" aria-hidden />
                </button>
              </div>

              <div className="divide-y divide-slate-100">
                {mealHistory.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    <p>Пока нет записей.</p>
                    <button
                      type="button"
                      onClick={() => openAddMeal()}
                      className="mt-3 font-semibold text-green-700 underline hover:text-green-800"
                    >
                      Добавить приём пищи
                    </button>
                  </div>
                ) : (
                  mealHistory.map((meal) => (
                    <div key={meal.id} className="flex items-start gap-4 p-4 transition hover:bg-slate-50 md:p-5">
                      {meal.thumbUrl ? (
                        <img
                          src={meal.thumbUrl}
                          alt={meal.predictionLine}
                          className="h-16 w-16 shrink-0 rounded-xl object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <MealIconCard icon={meal.icon} />
                      )}
                      <div className="min-w-0 flex-1">
                        <h3 className="text-base font-semibold leading-snug text-slate-900">{meal.predictionLine}</h3>
                        <p className="mt-1 text-sm text-slate-600">
                          Приём пищи * {meal.time}
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-700">
                          <span className="font-medium text-slate-800">Состав:</span> {meal.composition}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="font-bold text-slate-900">{formatIntRu(meal.calories)} kcal</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="space-y-6 md:col-span-4">
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-50">
                    <Target className="h-5 w-5 text-green-600" aria-hidden />
                  </div>
                  <h2 className="text-xl font-semibold text-slate-900">Дневные цели</h2>
                </div>

                {dailyGoals.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    Цели не рассчитаны. Заполните профиль (вес, цель, активность), чтобы появились нормы КБЖУ.
                  </p>
                ) : (
                  <div className="space-y-5">
                    {dailyGoals.map((item) => (
                      <DailyGoalProgress key={item.id} item={item} />
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-green-100 bg-green-50 p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white">
                    <Info className="h-5 w-5 text-green-600" aria-hidden />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-green-950">Совет ИИ</p>
                    <p className="mt-1 text-sm text-slate-600">Пейте больше воды сегодня!</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
