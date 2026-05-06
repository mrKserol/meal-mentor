import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  Info,
  Plus,
  Scale,
  X,
} from "lucide-react";

import { getMyNutritionTarget } from "../api/authApi";
import { addMyWeightMeasurement, getMyDiary, getMyWeightMeasurements } from "../api/diaryApi";
import { MealHistoryDaySection } from "../components/diary/MealHistoryDaySection";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";
import type {
  DiaryPeriodDay,
  DiarySnapshot,
  DiaryWeekDay,
  WeightMeasurementPeriod,
  WeightMeasurementPoint,
} from "../types/diary";
import type { NutritionTarget } from "../types/auth";

const MEAL_MENTOR_ACCESS_TOKEN_KEY = "meal_mentor_access_token";

type ChartDay = DiaryWeekDay | DiaryPeriodDay;
const ANALYSIS_GROUPS: { title: string; items: Array<{ key: string; label: string; unit: string }> }[] = [
  {
    title: "Витамины",
    items: [
      { key: "vitamin_a_mcg", label: "Витамин А", unit: "mcg" },
      { key: "vitamin_a_rae_mcg", label: "Витамин А RAE", unit: "mcg" },
      { key: "vitamin_c_mg", label: "Витамин С", unit: "mg" },
      { key: "vitamin_d_mcg", label: "Витамин D", unit: "mcg" },
      { key: "vitamin_e_mg", label: "Витамин Е", unit: "mg" },
      { key: "vitamin_k_mcg", label: "Витамин K", unit: "mcg" },
      { key: "vitamin_b6_mg", label: "Витамин B6", unit: "mg" },
      { key: "vitamin_b12_mcg", label: "Витамин B12", unit: "mcg" },
      { key: "thiamin_mg", label: "Тиамин (витамин B1)", unit: "mg" },
      { key: "riboflavin_mg", label: "Рибофлавин (витамин B2)", unit: "mg" },
      { key: "niacin_mg", label: "Ниацин (витамин B3)", unit: "mg" },
      { key: "folate_mcg", label: "Фолат (витамин B9)", unit: "mcg" },
      { key: "folic_acid_mcg", label: "Фолиевая кислота", unit: "mcg" },
      { key: "pantothenic_acid_mg", label: "Пантотеновая кислота (витамин B5)", unit: "mg" },
      { key: "tocopherol_alpha_mg", label: "Токоферол альфа", unit: "mg" },
      { key: "carotene_alpha_mcg", label: "Каротин альфа", unit: "mcg" },
      { key: "carotene_beta_mcg", label: "Каротин бета", unit: "mcg" },
      { key: "cryptoxanthin_beta_mcg", label: "Криптоксантин бета", unit: "mcg" },
      { key: "lutein_zeaxanthin_mcg", label: "Лютеин и зеаксантин", unit: "mcg" },
      { key: "lycopene_mcg", label: "Ликопин", unit: "mcg" },
      { key: "choline_mg", label: "Холин", unit: "mg" },
    ],
  },
  {
    title: "Минералы",
    items: [
      { key: "calcium_mg", label: "Кальций", unit: "mg" },
      { key: "magnesium_mg", label: "Магний", unit: "mg" },
      { key: "potassium_mg", label: "Калий", unit: "mg" },
      { key: "phosphorus_mg", label: "Фосфор", unit: "mg" },
      { key: "iron_mg", label: "Железо", unit: "mg" },
      { key: "zinc_mg", label: "Цинк", unit: "mg" },
      { key: "selenium_mcg", label: "Селен", unit: "mcg" },
      { key: "copper_mg", label: "Медь", unit: "mg" },
      { key: "manganese_mg", label: "Марганец", unit: "mg" },
      { key: "sodium_mg", label: "Натрий", unit: "mg" },
    ],
  },
  {
    title: "Аминокислоты",
    items: [
      { key: "alanine_g", label: "Аланин", unit: "g" },
      { key: "arginine_g", label: "Аргинин", unit: "g" },
      { key: "aspartic_acid_g", label: "Аспарагиновая кислота", unit: "g" },
      { key: "cystine_g", label: "Цистин", unit: "g" },
      { key: "glutamic_acid_g", label: "Глутаминовая кислота", unit: "g" },
      { key: "glycine_g", label: "Глицин", unit: "g" },
      { key: "histidine_g", label: "Гистидин", unit: "g" },
      { key: "hydroxyproline_g", label: "Гидроксипролин", unit: "g" },
      { key: "isoleucine_g", label: "Изолейцин", unit: "g" },
      { key: "leucine_g", label: "Лейцин", unit: "g" },
      { key: "lysine_g", label: "Лизин", unit: "g" },
      { key: "methionine_g", label: "Метионин", unit: "g" },
      { key: "phenylalanine_g", label: "Фенилаланин", unit: "g" },
      { key: "proline_g", label: "Пролин", unit: "g" },
      { key: "serine_g", label: "Серин", unit: "g" },
      { key: "threonine_g", label: "Треонин", unit: "g" },
      { key: "tryptophan_g", label: "Триптофан", unit: "g" },
      { key: "tyrosine_g", label: "Тирозин", unit: "g" },
      { key: "valine_g", label: "Валин", unit: "g" },
    ],
  },
  {
    title: "Жиры",
    items: [
      { key: "total_fat_g", label: "Жиры всего", unit: "g" },
      { key: "saturated_fatty_acids_g", label: "Насыщенные жирные кислоты", unit: "g" },
      { key: "monounsaturated_fatty_acids_g", label: "Мононенасыщенные жирные кислоты", unit: "g" },
      { key: "polyunsaturated_fatty_acids_g", label: "Полиненасыщенные жирные кислоты", unit: "g" },
      { key: "fatty_acids_total_trans_g", label: "Трансжиры", unit: "g" },
    ],
  },
  {
    title: "Сахара",
    items: [
      { key: "sugar_g", label: "Сахар", unit: "g" },
      { key: "fructose_g", label: "Фруктоза", unit: "g" },
      { key: "glucose_g", label: "Глюкоза", unit: "g" },
      { key: "lactose_g", label: "Лактоза", unit: "g" },
      { key: "galactose_g", label: "Галактоза", unit: "g" },
      { key: "maltose_g", label: "Мальтоза", unit: "g" },
      { key: "sucrose_g", label: "Сахароза", unit: "g" },
    ],
  },
  {
    title: "Дополнительно",
    items: [
      { key: "cholesterol_mg", label: "Холестерин", unit: "mg" },
      { key: "water_g", label: "Вода", unit: "g" },
      { key: "alcohol_g", label: "Алкоголь", unit: "g" },
      { key: "caffeine_mg", label: "Кофеин", unit: "mg" },
      { key: "theobromine_mg", label: "Теобромин", unit: "mg" },
    ],
  },
];

const WEIGHT_PERIOD_OPTIONS: { value: WeightMeasurementPeriod; label: string }[] = [
  { value: "1m", label: "1 м" },
  { value: "3m", label: "3 м" },
  { value: "6m", label: "6 м" },
  { value: "1y", label: "1 г" },
  { value: "all", label: "Всё время" },
];

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

function formatWeightDateLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit" }).format(d);
}

function WeightTrendChart({ items }: { items: WeightMeasurementPoint[] }) {
  if (items.length === 0) {
    return (
      <div className="flex h-36 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
        Пока нет взвешиваний
      </div>
    );
  }

  const chartWidth = Math.max(320, items.length * 56);
  const chartHeight = 150;
  const padX = 28;
  const padTop = 18;
  const padBottom = 34;
  const weights = items.map((it) => it.weight_kg);
  const minW = Math.min(...weights);
  const maxW = Math.max(...weights);
  const range = Math.max(maxW - minW, 1);
  const plotH = chartHeight - padTop - padBottom;
  const plotW = chartWidth - padX * 2;
  const points = items.map((it, index) => {
    const x = items.length === 1 ? chartWidth / 2 : padX + (plotW * index) / (items.length - 1);
    const y = padTop + ((maxW - it.weight_kg) / range) * plotH;
    return { x, y, item: it };
  });
  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <div className="w-full min-w-0">
      <svg
        width="100%"
        height={chartHeight}
        className="block min-h-[150px] w-full max-w-none"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="График изменения веса"
      >
        <line x1={padX} x2={chartWidth - padX} y1={padTop + plotH} y2={padTop + plotH} stroke="#e2e8f0" />
        <line x1={padX} x2={chartWidth - padX} y1={padTop} y2={padTop} stroke="#f1f5f9" />
        {items.length > 1 ? (
          <polyline points={polyline} fill="none" stroke="#15803d" strokeLinecap="round" strokeWidth="3" />
        ) : null}
        {points.map(({ x, y, item }, index) => (
          <g key={item.id}>
            <circle cx={x} cy={y} fill="#15803d" r="4" />
            <text x={x} y={Math.max(12, y - 9)} fill="#334155" fontSize="11" fontWeight="700" textAnchor="middle">
              {formatFixedRu(item.weight_kg, 1)}
            </text>
            {index === 0 || index === points.length - 1 || items.length <= 6 ? (
              <text x={x} y={chartHeight - 10} fill="#94a3b8" fontSize="10" textAnchor="middle">
                {formatWeightDateLabel(item.measured_at)}
              </text>
            ) : null}
          </g>
        ))}
      </svg>
    </div>
  );
}

export function DiaryPage() {
  const navigate = useNavigate();
  const { user, validateSession, logout, getAccessToken } = useAuth();
  const statsChartScrollRef = useRef<HTMLDivElement | null>(null);
  const [snapshot, setSnapshot] = useState<DiarySnapshot | null>(null);
  const [nutritionTarget, setNutritionTarget] = useState<NutritionTarget | null>(null);
  const [diaryPhase, setDiaryPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [diaryError, setDiaryError] = useState<string | null>(null);
  const [statsPeriod, setStatsPeriod] = useState<"week" | "month">("week");
  const [weightPeriod, setWeightPeriod] = useState<WeightMeasurementPeriod>("3m");
  const [weightMeasurements, setWeightMeasurements] = useState<WeightMeasurementPoint[]>([]);
  const [weightPhase, setWeightPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [weightError, setWeightError] = useState<string | null>(null);
  const [weightModalOpen, setWeightModalOpen] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [newWeightKg, setNewWeightKg] = useState("");
  const [newWeightNotes, setNewWeightNotes] = useState("");
  const [weightSaving, setWeightSaving] = useState(false);
  const [weightSaveError, setWeightSaveError] = useState<string | null>(null);

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

  const loadWeightMeasurements = useCallback(async () => {
    setWeightPhase("loading");
    setWeightError(null);
    try {
      const token = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const res = await getMyWeightMeasurements(token, weightPeriod);
      setWeightMeasurements(res.items);
      setWeightPhase("ready");
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
            : "Не удалось загрузить взвешивания";
      setWeightError(message);
      setWeightPhase("error");
    }
  }, [getAccessToken, navigate, weightPeriod]);

  useEffect(() => {
    void validateSession();
  }, [validateSession]);

  useEffect(() => {
    if (!user) return;
    void loadDiary();
  }, [user?.id, loadDiary]);

  useEffect(() => {
    if (!user) return;
    void loadWeightMeasurements();
  }, [user?.id, loadWeightMeasurements]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  const webDiaryToken = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY) ?? "";

  const weightKg = snapshot?.weight.weight_kg ?? user?.weight_kg ?? null;

  const activeStats = (statsPeriod === "week" ? snapshot?.week : snapshot?.month) ?? null;
  const chartDays: ChartDay[] = (activeStats?.days ?? []) as ChartDay[];
  const isMonth = statsPeriod === "month";

  useEffect(() => {
    if (!isMonth) return;

    const scrollToLatestDays = () => {
      const el = statsChartScrollRef.current;
      if (!el) return;
      el.scrollLeft = el.scrollWidth - el.clientWidth;
    };

    const frame = window.requestAnimationFrame(scrollToLatestDays);
    return () => window.cancelAnimationFrame(frame);
  }, [chartDays.length, isMonth]);

  const closeWeightModal = useCallback(() => {
    if (weightSaving) return;
    setWeightModalOpen(false);
    setWeightSaveError(null);
  }, [weightSaving]);

  const handleSaveWeight = useCallback(async () => {
    const weight = Number(newWeightKg.replace(",", "."));
    if (!Number.isFinite(weight) || weight <= 0) {
      setWeightSaveError("Введите корректный вес.");
      return;
    }
    const token = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    setWeightSaving(true);
    setWeightSaveError(null);
    try {
      await addMyWeightMeasurement(token, {
        weight_kg: weight,
        ...(newWeightNotes.trim() ? { notes: newWeightNotes.trim() } : {}),
      });
      setWeightModalOpen(false);
      setNewWeightKg("");
      setNewWeightNotes("");
      await Promise.all([loadDiary(), loadWeightMeasurements()]);
    } catch (e) {
      const message =
        axios.isAxiosError(e) && e.response?.data?.detail != null
          ? String(e.response.data.detail)
          : e instanceof Error
            ? e.message
            : "Не удалось сохранить взвешивание";
      setWeightSaveError(message);
    } finally {
      setWeightSaving(false);
    }
  }, [
    getAccessToken,
    loadDiary,
    loadWeightMeasurements,
    navigate,
    newWeightKg,
    newWeightNotes,
  ]);

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

  return (
    <AppShell
      activeNav="diary"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      onMealSaved={() => void loadDiary()}
    >
      {() => (
        <div className="mx-auto w-full max-w-full overflow-x-hidden p-4 pb-8 lg:max-w-7xl lg:p-8">
          <div className="min-w-0 space-y-6">
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

              <div ref={statsChartScrollRef} className="-mx-2 min-w-0 overflow-x-auto overscroll-x-contain px-2">
                <div
                  className={[
                    "flex h-48 items-end",
                    isMonth ? "w-[620px] max-w-none justify-between gap-1 md:w-full" : "w-full justify-between gap-2",
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

              <div className="mt-6 grid grid-cols-2 gap-4 border-t border-slate-100 pt-5 text-center md:grid-cols-4 xl:grid-cols-8">
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
                <div>
                  <p className="text-xl font-bold text-emerald-700">
                    {formatFixedRu(activeStats?.avg_fiber_g ?? 0, 1)} г
                  </p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Клетчатка</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-rose-700">{formatFixedRu(activeStats?.avg_sugar_g ?? 0, 1)} г</p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Сахар</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-cyan-700">{formatFixedRu(activeStats?.avg_salt_g ?? 0, 2)} г</p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Соль</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-amber-700">
                    {formatFixedRu(activeStats?.avg_saturated_fat_g ?? 0, 1)} г
                  </p>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Насыщенные жиры</p>
                </div>
              </div>
              <div className="mt-5 flex w-full justify-center px-1">
                <button
                  type="button"
                  onClick={() => setAnalysisOpen(true)}
                  className="w-full max-w-full rounded-xl bg-green-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700"
                >
                  Нутриентный профиль
                </button>
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

            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              {WEIGHT_PERIOD_OPTIONS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setWeightPeriod(item.value)}
                  className={
                    weightPeriod === item.value
                      ? "rounded-full bg-green-100 px-3 py-1 font-medium text-green-700"
                      : "rounded-full px-3 py-1 font-medium text-slate-400 transition hover:bg-slate-100"
                  }
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="py-4">
              {weightPhase === "error" && weightError ? (
                <div className="flex h-36 items-center justify-center rounded-lg bg-red-50 px-4 text-center text-sm text-red-600">
                  {weightError}
                </div>
              ) : weightPhase === "loading" && weightMeasurements.length === 0 ? (
                <div className="flex h-36 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
                  Загружаем взвешивания…
                </div>
              ) : (
                <WeightTrendChart items={weightMeasurements} />
              )}
            </div>

            <div>
              <button
                type="button"
                onClick={() => {
                  setNewWeightKg(weightKg != null ? weightKg.toFixed(1) : "");
                  setWeightSaveError(null);
                  setWeightModalOpen(true);
                }}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700 sm:w-auto"
              >
                <Plus className="h-4 w-4" aria-hidden />
                Добавить взвешивание
              </button>
            </div>
          </section>

          {analysisOpen ? (
            <div
              className="fixed inset-0 z-[110] flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
              role="dialog"
              aria-modal="true"
              aria-labelledby="analysis-modal-title"
              onMouseDown={(e) => {
                if (e.target === e.currentTarget) setAnalysisOpen(false);
              }}
            >
              <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl">
                <div className="mb-4 flex items-center justify-between">
                  <h2 id="analysis-modal-title" className="text-xl font-semibold text-slate-900">
                    Нутриентный профиль (средние значения)
                  </h2>
                  <button
                    type="button"
                    onClick={() => setAnalysisOpen(false)}
                    className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                    aria-label="Закрыть"
                  >
                    <X className="h-5 w-5" aria-hidden />
                  </button>
                </div>
                <div className="space-y-5">
                  {ANALYSIS_GROUPS.map((group) => (
                    <section key={group.title} className="rounded-xl border border-slate-200 p-4">
                      <h3 className="mb-2 text-base font-semibold text-slate-900">{group.title}</h3>
                      <div className="space-y-1">
                        {group.items.map((item) => (
                          <p key={item.key} className="text-sm text-slate-700">
                            {item.label} - {formatFixedRu(activeStats?.detailed_avg?.[item.key] ?? 0, 3)} {item.unit}
                          </p>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {weightModalOpen ? (
            <div
              className="fixed inset-0 z-[100] flex items-end justify-center bg-black/45 p-0 sm:items-center sm:p-4"
              role="dialog"
              aria-modal="true"
              aria-labelledby="weight-modal-title"
              onMouseDown={(e) => {
                if (e.target === e.currentTarget) closeWeightModal();
              }}
            >
              <div className="w-full max-w-md rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 id="weight-modal-title" className="text-xl font-semibold text-slate-900">
                    Добавить взвешивание
                  </h2>
                  <button
                    type="button"
                    onClick={closeWeightModal}
                    className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                    aria-label="Закрыть"
                  >
                    <X className="h-5 w-5" aria-hidden />
                  </button>
                </div>

                <div className="space-y-4">
                  <label className="flex flex-col gap-1">
                    <span className="text-sm font-medium text-slate-600">Вес, кг</span>
                    <input
                      type="number"
                      min={1}
                      step="0.1"
                      inputMode="decimal"
                      value={newWeightKg}
                      onChange={(e) => setNewWeightKg(e.target.value)}
                      className="h-12 w-full rounded-lg border border-slate-200 bg-slate-50 px-4 text-base outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                    />
                  </label>

                  <label className="flex flex-col gap-1">
                    <span className="text-sm font-medium text-slate-600">Заметка</span>
                    <textarea
                      value={newWeightNotes}
                      onChange={(e) => setNewWeightNotes(e.target.value)}
                      rows={3}
                      className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-base outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                    />
                  </label>

                  {weightSaveError ? <p className="text-sm text-red-600">{weightSaveError}</p> : null}

                  <button
                    type="button"
                    onClick={() => void handleSaveWeight()}
                    disabled={weightSaving}
                    className="flex w-full items-center justify-center rounded-lg bg-green-600 px-4 py-3 font-semibold text-white transition hover:bg-green-700 disabled:opacity-60"
                  >
                    {weightSaving ? "Сохраняем..." : "Сохранить"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
          </div>
        </div>
      )}
    </AppShell>
  );
}
