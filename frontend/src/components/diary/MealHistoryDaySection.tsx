import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Apple, Beef, ChevronLeft, ChevronRight, Coffee, EggFried, Flame, Leaf, Salad, Target, Wheat, X } from "lucide-react";

import { getMyNutritionTarget } from "../../api/authApi";
import { deleteMyMeal, getMyMealsForDay } from "../../api/diaryApi";
import { EditMealModal } from "../layout/EditMealModal";
import { MealMacroInline, MealMacroLines } from "../meals/MealMacroLines";
import type { NutritionTarget } from "../../types/auth";
import type { WebMealDayItemLine, WebMealDayRow } from "../../types/mealsDay";
import { formatIntRu, formatMacroGramsRu } from "../../utils/recentMeals";

const DELETE_PANEL_PX = 96;

type GoalIconKind = "calories" | "protein" | "fat" | "carbs" | "fiber";

type DayGoalItem = {
  id: string;
  label: string;
  current: string;
  target: string;
  percent: number;
  tone: "green" | "orange" | "slate";
  icon: GoalIconKind;
};

function formatLocalYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDaysYmd(ymd: string, delta: number): string {
  const [y, mo, da] = ymd.split("-").map(Number);
  const dt = new Date(y, mo - 1, da + delta);
  return formatLocalYmd(dt);
}

function ymdToRuLong(ymd: string): string {
  const [y, mo, da] = ymd.split("-").map(Number);
  const dt = new Date(y, mo - 1, da);
  return new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(
    dt,
  );
}

function getMealIcon(mt: string | null) {
  const m = (mt || "").toLowerCase();
  if (m === "breakfast") return Coffee;
  if (m === "lunch" || m === "dinner") return Salad;
  return Apple;
}

function pctCurrentTarget(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.min(100, Math.round((100 * current) / target));
}

function goalToneFromPercent(percent: number): DayGoalItem["tone"] {
  if (percent >= 100) return "orange";
  if (percent >= 60) return "green";
  return "slate";
}

function getGoalIcon(icon: GoalIconKind) {
  if (icon === "calories") return Flame;
  if (icon === "protein") return Beef;
  if (icon === "fat") return EggFried;
  if (icon === "fiber") return Leaf;
  return Wheat;
}

function goalStrokeClass(tone: DayGoalItem["tone"]): string {
  if (tone === "green") return "stroke-green-600";
  if (tone === "orange") return "stroke-orange-500";
  return "stroke-slate-700";
}

function goalIconClass(tone: DayGoalItem["tone"]): string {
  if (tone === "green") return "text-green-600";
  if (tone === "orange") return "text-orange-500";
  return "text-slate-700";
}

function buildDayGoals(nutritionTarget: NutritionTarget | null, meals: WebMealDayRow[]): DayGoalItem[] {
  if (!nutritionTarget) return [];

  const totals = meals.reduce(
    (acc, meal) => ({
      calories: acc.calories + meal.calories,
      protein_g: acc.protein_g + (meal.protein_g ?? 0),
      fat_g: acc.fat_g + (meal.fat_g ?? 0),
      carbs_g: acc.carbs_g + (meal.carbs_g ?? 0),
      fiber_g: acc.fiber_g + (meal.fiber_g ?? 0),
    }),
    { calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0, fiber_g: 0 },
  );

  const c = pctCurrentTarget(totals.calories, nutritionTarget.target_calories);
  const p = pctCurrentTarget(totals.protein_g, nutritionTarget.target_protein_g);
  const f = pctCurrentTarget(totals.fat_g, nutritionTarget.target_fat_g);
  const cb = pctCurrentTarget(totals.carbs_g, nutritionTarget.target_carbs_g);
  const fib = pctCurrentTarget(totals.fiber_g, nutritionTarget.target_fiber_g);

  return [
    {
      id: "calories",
      label: "Калории",
      current: formatIntRu(totals.calories),
      target: `${formatIntRu(nutritionTarget.target_calories)} kcal`,
      percent: c,
      tone: goalToneFromPercent(c),
      icon: "calories",
    },
    {
      id: "protein",
      label: "Белки",
      current: formatIntRu(totals.protein_g),
      target: `${formatIntRu(nutritionTarget.target_protein_g)} г`,
      percent: p,
      tone: goalToneFromPercent(p),
      icon: "protein",
    },
    {
      id: "fat",
      label: "Жиры",
      current: formatIntRu(totals.fat_g),
      target: `${formatIntRu(nutritionTarget.target_fat_g)} г`,
      percent: f,
      tone: goalToneFromPercent(f),
      icon: "fat",
    },
    {
      id: "carbs",
      label: "Углеводы",
      current: formatIntRu(totals.carbs_g),
      target: `${formatIntRu(nutritionTarget.target_carbs_g)} г`,
      percent: cb,
      tone: goalToneFromPercent(cb),
      icon: "carbs",
    },
    {
      id: "fiber",
      label: "Клетчатка",
      current: formatIntRu(totals.fiber_g),
      target: `${formatMacroGramsRu(nutritionTarget.target_fiber_g)} г`,
      percent: fib,
      tone: goalToneFromPercent(fib),
      icon: "fiber",
    },
  ];
}

function DayGoalProgress({ item }: { item: DayGoalItem }) {
  const Icon = getGoalIcon(item.icon);
  const strokeClass = goalStrokeClass(item.tone);
  const iconClass = goalIconClass(item.tone);

  return (
    <div className="flex min-w-0 items-center gap-2">
      <div className="relative h-9 w-9 shrink-0">
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
          <Icon className={`h-4 w-4 ${iconClass}`} aria-hidden />
        </div>
      </div>
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-slate-900">{item.label}</p>
        <p className="whitespace-nowrap text-[11px] text-slate-500">
          {item.current} / {item.target}
        </p>
      </div>
      <span className="ml-auto shrink-0 text-xs font-bold text-slate-700">{item.percent}%</span>
    </div>
  );
}

function MealIconCard({ mealType }: { mealType: string | null }) {
  const Icon = getMealIcon(mealType);
  return (
    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
      <Icon className="h-7 w-7" aria-hidden />
    </div>
  );
}

function predictionHeading(m: WebMealDayRow): string {
  const p = (m.prediction || "").trim();
  if (p) return p;
  const u = (m.user_text || "").trim();
  if (u) return u.length <= 120 ? u : `${u.slice(0, 119)}…`;
  return "—";
}

function SwipeMealRow({
  children,
  onDelete,
  onOpen,
  disabled,
}: {
  children: ReactNode;
  onDelete: () => void;
  onOpen: () => void;
  disabled?: boolean;
}) {
  const [offset, setOffset] = useState(0);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startOffset = useRef(0);
  const pointerId = useRef<number | null>(null);
  const maxAbsDx = useRef(0);
  const suppressOpen = useRef(false);
  const offsetRef = useRef(0);
  offsetRef.current = offset;

  const clamp = useCallback((v: number) => Math.min(0, Math.max(-DELETE_PANEL_PX, v)), []);

  const onPointerDown = (e: React.PointerEvent) => {
    if (disabled) return;
    if (e.button !== 0) return;
    dragging.current = true;
    startX.current = e.clientX;
    startOffset.current = offset;
    maxAbsDx.current = 0;
    suppressOpen.current = false;
    pointerId.current = e.pointerId;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current || pointerId.current !== e.pointerId) return;
    const dx = e.clientX - startX.current;
    maxAbsDx.current = Math.max(maxAbsDx.current, Math.abs(dx));
    if (maxAbsDx.current > 12) suppressOpen.current = true;
    setOffset(clamp(startOffset.current + dx));
  };

  const endDrag = (e: React.PointerEvent) => {
    if (pointerId.current !== e.pointerId) return;
    dragging.current = false;
    pointerId.current = null;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    setOffset((cur) => (cur < -DELETE_PANEL_PX / 2 ? -DELETE_PANEL_PX : 0));
  };

  const handleTap = () => {
    if (suppressOpen.current) return;
    if (offsetRef.current !== 0) {
      setOffset(0);
      return;
    }
    onOpen();
  };

  return (
    <div className="relative overflow-hidden border-b border-slate-100 last:border-b-0">
      <div
        className="absolute inset-y-0 right-0 z-0 flex w-[96px] items-stretch justify-stretch bg-red-600"
        aria-hidden={offset === 0}
      >
        <button
          type="button"
          disabled={disabled}
          onClick={(ev) => {
            ev.stopPropagation();
            void onDelete();
          }}
          className="w-full text-center text-sm font-bold text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          Удалить
        </button>
      </div>
      <div
        role="presentation"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClick={handleTap}
        style={{
          transform: `translateX(${offset}px)`,
          touchAction: "pan-y",
        }}
        className="relative z-10 cursor-pointer bg-white"
      >
        {children}
      </div>
    </div>
  );
}

function mealTotalsMacros(m: WebMealDayRow): { p: number; f: number; c: number } {
  return {
    p: m.protein_g ?? 0,
    f: m.fat_g ?? 0,
    c: m.carbs_g ?? 0,
  };
}

function sodiumMgToSaltG(sodiumMg: number): number {
  return Number((sodiumMg / 1000).toFixed(2));
}

function itemLineMacros(it: WebMealDayItemLine): { p: number; f: number; c: number; fiber: number } {
  return {
    p: it.protein_g ?? 0,
    f: it.fat_g ?? 0,
    c: it.carbs_g ?? 0,
    fiber: it.fiber_g ?? 0,
  };
}

function MealDayDetailModal({
  meal,
  onClose,
  onEdit,
}: {
  meal: WebMealDayRow;
  onClose: () => void;
  onEdit: () => void;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const large = meal.meal_photo_large_url || meal.meal_photo_thumb_url;
  const pred = predictionHeading(meal);
  const totM = mealTotalsMacros(meal);
  const totalFiber = meal.fiber_g ?? 0;
  const totalSugar = meal.sugar_g ?? 0;
  const totalSalt = sodiumMgToSaltG(meal.sodium_mg ?? 0);
  const totalSatFat = meal.saturated_fat_g ?? 0;
  const totalWater = meal.water_g ?? 0;
  useEffect(() => {
    setDetailsOpen(false);
  }, [meal.id]);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="meal-detail-title"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white shadow-xl sm:rounded-2xl">
        <div className="sticky top-0 z-10 flex justify-end border-b border-slate-100 bg-white/95 px-2 py-1 backdrop-blur">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
            aria-label="Закрыть"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        {large ? (
          <div className="bg-slate-900">
            <img src={large} alt="" className="mx-auto max-h-[min(55vh,480px)] w-full object-contain" />
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center bg-slate-100 text-slate-400">Нет фото</div>
        )}
        <div className="space-y-3 p-5">
          <h2 id="meal-detail-title" className="text-xl font-semibold leading-snug text-slate-900">
            {pred}
          </h2>
          <p className="text-sm text-slate-600">Приём пищи в {meal.time_local}</p>
          <p className="text-sm leading-relaxed text-slate-800">
            <span className="font-medium text-slate-900">Состав:</span> {meal.composition}
          </p>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-900">{formatIntRu(meal.calories)} kcal</p>
            <MealMacroInline proteinG={totM.p} fatG={totM.f} carbsG={totM.c} className="text-sm font-normal" />
          </div>

          <div className="space-y-2">
              <button
                type="button"
                onClick={() => setDetailsOpen((open) => !open)}
                aria-expanded={detailsOpen}
                className="flex w-full items-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                {detailsOpen ? "− Подробнее" : "+ Подробнее"}
              </button>
              {detailsOpen ? (
                <div className="space-y-3">
                  <p className="text-sm text-slate-600">
                    Клетчатка: {formatMacroGramsRu(totalFiber)} г · Сахар: {formatMacroGramsRu(totalSugar)} г · Соль:{" "}
                    {formatMacroGramsRu(totalSalt)} г · Насыщенные жиры: {formatMacroGramsRu(totalSatFat)} г · Вода:{" "}
                    {formatMacroGramsRu(totalWater)} г
                  </p>
                  {meal.items.length > 0 ? (
                  <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100 text-sm">
                    {meal.items.map((it) => {
                      const im = itemLineMacros(it);
                      return (
                        <li key={it.id} className="flex flex-wrap items-start justify-between gap-2 px-3 py-2">
                          <div className="min-w-0 flex-1">
                            <span className="text-slate-800">
                              {it.item_name || "—"}
                              {it.estimated_weight_g != null ? ` · ${it.estimated_weight_g} г` : ""}
                            </span>
                            <MealMacroInline
                              proteinG={im.p}
                              fatG={im.f}
                              carbsG={im.c}
                              fiberG={im.fiber}
                              className="mt-1 block text-xs text-slate-500"
                            />
                          </div>
                          <div className="shrink-0 text-right text-slate-500">
                            {it.calories != null ? (
                              <span className="block whitespace-nowrap">{formatIntRu(it.calories)} kcal</span>
                            ) : null}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                  ) : null}
                </div>
              ) : null}
            </div>

          <button
            type="button"
            onClick={onEdit}
            className="w-full rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-green-700"
          >
            Редактировать
          </button>
        </div>
      </div>
    </div>
  );
}

function MealDayRowContent({ meal }: { meal: WebMealDayRow }) {
  const thumb = meal.meal_photo_thumb_url;
  const pred = predictionHeading(meal);
  const tm = mealTotalsMacros(meal);

  return (
    <div className="flex w-full items-start gap-3 p-4 text-left transition hover:bg-slate-50 md:p-5">
      <div className="flex w-[4.5rem] shrink-0 flex-col items-end pt-0.5 sm:w-16">
        <span className="text-base font-bold leading-none text-slate-900">{formatIntRu(meal.calories)}</span>
        <span className="mt-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">kcal</span>
        <MealMacroLines proteinG={tm.p} fatG={tm.f} carbsG={tm.c} className="mt-1" />
      </div>
      {thumb ? (
        <img src={thumb} alt="" className="h-16 w-16 shrink-0 rounded-xl object-cover" loading="lazy" />
      ) : (
        <MealIconCard mealType={meal.meal_type} />
      )}
      <div className="min-w-0 flex-1">
        <h3 className="text-base font-semibold leading-snug text-slate-900">{pred}</h3>
        <p className="mt-1 text-sm text-slate-600">Приём пищи в {meal.time_local}</p>
        <p className="mt-2 hidden text-sm leading-relaxed text-slate-700 md:block">
          <span className="font-medium text-slate-800">Состав:</span> {meal.composition}
        </p>
      </div>
    </div>
  );
}

interface MealHistoryDaySectionProps {
  accessToken: string;
  nutritionTarget: NutritionTarget | null;
  onMealsChanged?: () => void;
  onAddMealForDay?: (dateYmd: string) => void;
}

export function MealHistoryDaySection({
  accessToken,
  nutritionTarget,
  onMealsChanged,
  onAddMealForDay,
}: MealHistoryDaySectionProps) {
  const [day, setDay] = useState(() => formatLocalYmd(new Date()));
  const [items, setItems] = useState<WebMealDayRow[]>([]);
  const [dayNutritionTarget, setDayNutritionTarget] = useState<NutritionTarget | null>(nutritionTarget);
  const [phase, setPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<WebMealDayRow | null>(null);
  const [editingMeal, setEditingMeal] = useState<WebMealDayRow | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setPhase("loading");
    setError(null);
    try {
      const [mealsRes, targetRes] = await Promise.all([
        getMyMealsForDay(accessToken, day),
        getMyNutritionTarget(accessToken, day),
      ]);
      setItems(mealsRes.items);
      setDayNutritionTarget(targetRes.nutrition_target);
      setPhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить приёмы");
      setPhase("error");
    }
  }, [accessToken, day]);

  useEffect(() => {
    void load();
  }, [load]);

  const todayYmd = useMemo(() => formatLocalYmd(new Date()), []);
  const isToday = day === todayYmd;
  const dateLabel = useMemo(() => ymdToRuLong(day), [day]);
  const dayGoals = useMemo(() => buildDayGoals(dayNutritionTarget, items), [dayNutritionTarget, items]);

  useEffect(() => {
    if (day > todayYmd) setDay(todayYmd);
  }, [day, todayYmd]);

  const handleDelete = async (id: number) => {
    if (deletingId != null) return;
    setDeletingId(id);
    try {
      await deleteMyMeal(accessToken, id);
      setDetail((d) => (d?.id === id ? null : d));
      await load();
      onMealsChanged?.();
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-5 md:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold text-slate-900">История приёмов пищи</h2>
            <p className="mt-1 text-sm capitalize text-slate-500">{dateLabel}</p>
            <div className="mt-4 flex items-center gap-1">
              <button
                type="button"
                onClick={() => setDay((d) => addDaysYmd(d, -1))}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50"
                aria-label="Предыдущий день"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <input
                type="date"
                value={day}
                max={todayYmd}
                onChange={(e) => {
                  const v = e.target.value;
                  if (!v) return;
                  setDay(v > todayYmd ? todayYmd : v);
                }}
                className="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800"
              />
              <button
                type="button"
                onClick={() => setDay((d) => (addDaysYmd(d, 1) > todayYmd ? d : addDaysYmd(d, 1)))}
                disabled={isToday}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Следующий день"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
            {onAddMealForDay ? (
              <button
                type="button"
                onClick={() => onAddMealForDay(day)}
                disabled={isToday}
                title={
                  isToday
                    ? "Для сегодняшнего дня используйте кнопку «+» в меню"
                    : "Добавить приём за выбранный день (23:59)"
                }
                className="mt-3 w-full rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:hover:bg-slate-300 sm:w-auto sm:min-w-[10rem]"
              >
                Добавить
              </button>
            ) : null}
          </div>

          <div className="w-full rounded-xl border border-slate-100 bg-slate-50/70 p-4 xl:max-w-2xl">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white">
                <Target className="h-4 w-4 text-green-600" aria-hidden />
              </div>
              <h3 className="text-sm font-semibold text-slate-900">Дневные нормы</h3>
            </div>

            {dayGoals.length === 0 ? (
              <p className="text-sm text-slate-500">
                Цели не рассчитаны. Заполните профиль (вес, цель, активность), чтобы появились нормы КБЖУ.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {dayGoals.map((item) => (
                  <DayGoalProgress key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {phase === "loading" && items.length === 0 ? (
        <p className="p-8 text-center text-slate-500">Загрузка…</p>
      ) : null}
      {phase === "error" && error ? (
        <p className="p-6 text-center text-sm text-red-600">{error}</p>
      ) : null}
      {phase === "ready" && items.length === 0 ? (
        <div className="p-8 text-center text-slate-500">
          <p>За этот день записей нет.</p>
        </div>
      ) : null}

      <div>
        {items.map((meal) => (
          <SwipeMealRow
            key={meal.id}
            disabled={deletingId === meal.id}
            onDelete={() => void handleDelete(meal.id)}
            onOpen={() => setDetail(meal)}
          >
            <MealDayRowContent meal={meal} />
          </SwipeMealRow>
        ))}
      </div>

      {detail ? (
        <MealDayDetailModal
          meal={detail}
          onClose={() => setDetail(null)}
          onEdit={() => {
            setEditingMeal(detail);
            setDetail(null);
          }}
        />
      ) : null}

      <EditMealModal
        open={editingMeal != null}
        meal={editingMeal}
        accessToken={accessToken}
        onClose={() => setEditingMeal(null)}
        onSaved={() => {
          void load();
          onMealsChanged?.();
        }}
      />
    </section>
  );
}
