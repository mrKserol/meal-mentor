import { useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Apple,
  BarChart3,
  Camera,
  ChevronRight,
  CirclePlus,
  Coffee,
  Droplets,
  Flame,
  Info,
  Salad,
  Scale,
  Sparkles,
  Target,
  Utensils,
} from "lucide-react";

import { AppShell } from "../components/layout/AppShell";
import { defaultNewMealHandler } from "../components/layout/appNav";
import { useAuth } from "../hooks/useAuth";

type WeekStat = {
  day: string;
  containerHeight: number;
  valueHeight: number;
};

type MealHistoryItem = {
  id: string;
  title: string;
  mealType: string;
  time: string;
  calories: number;
  tag: string;
  icon: "breakfast" | "lunch" | "snack";
  tagTone: "green" | "slate";
};

type DailyGoalItem = {
  id: string;
  label: string;
  current: string;
  target: string;
  percent: number;
  tone: "green" | "orange" | "slate";
  icon: "calories" | "protein" | "water";
};

/** Mock: позже заменить данными с API */
const weekStats: WeekStat[] = [
  { day: "Пн", containerHeight: 60, valueHeight: 80 },
  { day: "Вт", containerHeight: 75, valueHeight: 90 },
  { day: "Ср", containerHeight: 50, valueHeight: 40 },
  { day: "Чт", containerHeight: 90, valueHeight: 95 },
  { day: "Пт", containerHeight: 65, valueHeight: 70 },
  { day: "Сб", containerHeight: 40, valueHeight: 30 },
  { day: "Вс", containerHeight: 55, valueHeight: 50 },
];

const mealHistory: MealHistoryItem[] = [
  {
    id: "breakfast",
    title: "Овсянка с ягодами",
    mealType: "Завтрак",
    time: "08:30",
    calories: 420,
    tag: "Много белка",
    icon: "breakfast",
    tagTone: "green",
  },
  {
    id: "lunch",
    title: "Куриный салат",
    mealType: "Обед",
    time: "12:45",
    calories: 580,
    tag: "Мало углеводов",
    icon: "lunch",
    tagTone: "green",
  },
  {
    id: "snack",
    title: "Зелёное яблоко",
    mealType: "Перекус",
    time: "16:15",
    calories: 95,
    tag: "Перекус",
    icon: "snack",
    tagTone: "slate",
  },
];

const dailyGoals: DailyGoalItem[] = [
  {
    id: "calories",
    label: "Калории",
    current: "1 580",
    target: "2 100 kcal",
    percent: 75,
    tone: "green",
    icon: "calories",
  },
  {
    id: "protein",
    label: "Белки",
    current: "68",
    target: "150 г",
    percent: 45,
    tone: "orange",
    icon: "protein",
  },
  {
    id: "water",
    label: "Вода",
    current: "2.2",
    target: "2.5 л",
    percent: 90,
    tone: "slate",
    icon: "water",
  },
];

function getTodayRu(): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
  }).format(new Date());
}

function getMealIcon(icon: MealHistoryItem["icon"]) {
  if (icon === "breakfast") return Coffee;
  if (icon === "lunch") return Salad;
  return Apple;
}

function getGoalIcon(icon: DailyGoalItem["icon"]) {
  if (icon === "calories") return Flame;
  if (icon === "protein") return Utensils;
  return Droplets;
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
      <div>
        <p className="text-sm font-semibold text-slate-900">{item.label}</p>
        <p className="text-xs text-slate-500">
          {item.current} / {item.target}
        </p>
      </div>
      <span className="ml-auto text-sm font-bold text-slate-700">{item.percent}%</span>
    </div>
  );
}

export function DiaryPage() {
  const navigate = useNavigate();
  const { user, validateSession, logout } = useAuth();

  useEffect(() => {
    void validateSession();
  }, [validateSession]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <p className="text-base text-slate-500">Загрузка дневника...</p>
      </div>
    );
  }

  return (
    <AppShell
      activeNav="diary"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      onNewMeal={defaultNewMealHandler}
    >
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
            onClick={defaultNewMealHandler}
            className="flex items-center justify-center gap-2 rounded-lg bg-green-500 px-6 py-3 font-semibold text-green-950 shadow-sm transition hover:bg-green-400 active:scale-[0.98]"
          >
            <CirclePlus className="h-5 w-5" aria-hidden />
            Добавить приём пищи
          </button>
        </section>

        <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:col-span-2">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-50">
                  <BarChart3 className="h-5 w-5 text-green-600" aria-hidden />
                </div>
                <h2 className="text-xl font-semibold text-slate-900">Статистика за неделю</h2>
              </div>
              <div className="flex gap-2 text-sm">
                <span className="rounded-full bg-green-100 px-3 py-1 font-medium text-green-700">Неделя</span>
                <span className="rounded-full px-3 py-1 font-medium text-slate-400">Месяц</span>
              </div>
            </div>

            <div className="flex h-48 w-full items-end justify-between gap-2 px-2 pb-7">
              {weekStats.map((item) => (
                <div
                  key={item.day}
                  className="relative flex w-full items-end rounded-t-lg bg-slate-100"
                  style={{ height: `${item.containerHeight}%` }}
                >
                  <div
                    className="w-full rounded-t-lg bg-green-400"
                    style={{ height: `${item.valueHeight}%` }}
                  />
                  <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-slate-400">
                    {item.day}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4 border-t border-slate-100 pt-5 text-center md:grid-cols-4">
              <div>
                <p className="text-xl font-bold text-green-700">2 150</p>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Средние ккал</p>
              </div>
              <div>
                <p className="text-xl font-bold text-orange-600">145 г</p>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Белки</p>
              </div>
              <div>
                <p className="text-xl font-bold text-slate-900">65 г</p>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Жиры</p>
              </div>
              <div>
                <p className="text-xl font-bold text-slate-900">220 г</p>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Углеводы</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Текущий вес</h2>
                <p className="mt-1 text-3xl font-bold text-green-700">
                  74.2 <span className="text-sm font-semibold text-slate-400">кг</span>
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
                <span className="font-bold text-green-700">-0.8 кг</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100">
                <div className="h-full w-[65%] rounded-full bg-green-400" />
              </div>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-6 md:grid-cols-12">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm md:col-span-8">
            <div className="flex items-center justify-between border-b border-slate-100 p-6">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">История приёмов пищи</h2>
                <p className="mt-1 text-sm text-slate-500">Последние записи за сегодня</p>
              </div>
              <button
                type="button"
                className="flex items-center gap-1 text-sm font-bold text-green-700 transition hover:text-green-800"
              >
                Все
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </div>

            <div className="divide-y divide-slate-100">
              {mealHistory.map((meal) => (
                <div key={meal.id} className="flex items-center gap-4 p-4 transition hover:bg-slate-50 md:p-5">
                  <MealIconCard icon={meal.icon} />
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-base font-semibold text-slate-900">{meal.title}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {meal.mealType} • {meal.time}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-slate-900">{meal.calories} kcal</p>
                    <span
                      className={[
                        "mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                        meal.tagTone === "green"
                          ? "bg-green-50 text-green-700"
                          : "bg-slate-100 text-slate-500",
                      ].join(" ")}
                    >
                      {meal.tag}
                    </span>
                  </div>
                </div>
              ))}
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

              <div className="space-y-5">
                {dailyGoals.map((item) => (
                  <DailyGoalProgress key={item.id} item={item} />
                ))}
              </div>
            </div>

            <div className="overflow-hidden rounded-xl bg-gradient-to-br from-green-600 to-green-800 p-6 text-white shadow-lg shadow-green-900/20">
              <div className="mb-4 flex items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
                  <Sparkles className="h-5 w-5" aria-hidden />
                </div>
                <span className="rounded-full bg-white/20 px-2 py-1 text-xs font-bold uppercase tracking-wide">
                  Standard
                </span>
              </div>
              <h2 className="text-xl font-semibold">ИИ распознавание еды</h2>
              <p className="mt-2 text-sm leading-relaxed text-white/80">
                Разблокируйте фото-логирование еды и подробный анализ микронутриентов.
              </p>
              <button
                type="button"
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-white py-2.5 text-sm font-bold text-green-700 transition active:scale-[0.98]"
              >
                <Camera className="h-4 w-4" aria-hidden />
                Обновить до Pro
              </button>
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
    </AppShell>
  );
}
