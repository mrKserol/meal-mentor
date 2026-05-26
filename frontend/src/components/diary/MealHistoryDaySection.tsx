import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Apple, Beef, ChevronLeft, ChevronRight, Coffee, EggFried, Flame, Leaf, Salad, Target, Wheat, X } from "lucide-react";

import { getMyNutritionTarget } from "../../api/authApi";
import type { MyNutritionTargetEnvelope } from "../../types/auth";
import { deleteMyMeal, getMyMealsForDay, shiftMyMealDate } from "../../api/diaryApi";
import { EditMealModal } from "../layout/EditMealModal";
import { MealMacroInline, MealMacroLines } from "../meals/MealMacroLines";
import type { NutritionTarget } from "../../types/auth";
import { AdditiveIntakesDayModal } from "../additives/AdditiveIntakesDayModal";
import type { DayNutritionTotals, WebMealDayItemLine, WebMealDayRow, WebMealsDayResponse } from "../../types/mealsDay";
import { zeroDayNutritionTotals } from "../../types/mealsDay";
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

function buildDayGoals(
  nutritionTarget: NutritionTarget | null,
  meals: WebMealDayRow[],
  additiveTotals: DayNutritionTotals,
): DayGoalItem[] {
  if (!nutritionTarget) return [];

  const mealTotals = meals.reduce(
    (acc, meal) => ({
      calories: acc.calories + meal.calories,
      protein_g: acc.protein_g + (meal.protein_g ?? 0),
      fat_g: acc.fat_g + (meal.fat_g ?? 0),
      carbs_g: acc.carbs_g + (meal.carbs_g ?? 0),
      fiber_g: acc.fiber_g + (meal.fiber_g ?? 0),
    }),
    { calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0, fiber_g: 0 },
  );

  const totals = {
    calories: mealTotals.calories + additiveTotals.calories,
    protein_g: mealTotals.protein_g + additiveTotals.protein_g,
    fat_g: mealTotals.fat_g + additiveTotals.fat_g,
    carbs_g: mealTotals.carbs_g + additiveTotals.carbs_g,
    fiber_g: mealTotals.fiber_g + additiveTotals.fiber_g,
  };

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
  const p = (m.display_prediction || m.prediction_translated || m.prediction || "").trim();
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

function formatMealDateLine(dateLocal: string | undefined, timeLocal: string): string {
  if (!dateLocal) return `в ${timeLocal}`;
  const [y, m, d] = dateLocal.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const weekday = new Intl.DateTimeFormat("ru-RU", { weekday: "long" }).format(dt);
  const dayMonth = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" }).format(dt);
  const weekdayCap = weekday.charAt(0).toUpperCase() + weekday.slice(1);
  return `${weekdayCap}, ${dayMonth} в ${timeLocal}`;
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
  onShiftDate,
  onDelete,
  readonly = false,
  shiftingDate = false,
  deleting = false,
}: {
  meal: WebMealDayRow;
  onClose: () => void;
  onEdit: () => void;
  onShiftDate?: (delta: 1 | -1) => void;
  onDelete?: () => void;
  readonly?: boolean;
  shiftingDate?: boolean;
  deleting?: boolean;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [shiftConfirm, setShiftConfirm] = useState<1 | -1 | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);
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
            <button
              type="button"
              onClick={() => setLightboxOpen(true)}
              className="block w-full cursor-zoom-in"
              aria-label="Увеличить фото"
            >
              <img src={large} alt="" className="mx-auto max-h-[min(55vh,480px)] w-full object-contain" />
            </button>
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center bg-slate-100 text-slate-400">Нет фото</div>
        )}
        <div className="space-y-3 p-5">
          <h2 id="meal-detail-title" className="text-xl font-semibold leading-snug text-slate-900">
            {pred}
          </h2>
          <p className="text-sm font-medium text-slate-500">{formatMealDateLine(meal.date_local, meal.time_local)}</p>
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
                              {it.display_name || it.name_translated || it.item_name || "—"}
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

          {!readonly ? (
            <div className="space-y-2">
              <button
                type="button"
                onClick={onEdit}
                className="w-full rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-green-700"
              >
                Редактировать
              </button>

              {onShiftDate ? (
                shiftConfirm !== null ? (
                  <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5">
                    <span className="flex-1 text-sm font-medium text-slate-700">
                      {shiftConfirm === -1
                        ? "Переместить приём пищи на день назад?"
                        : "Переместить приём пищи на день вперёд?"}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        const delta = shiftConfirm;
                        setShiftConfirm(null);
                        onShiftDate(delta);
                      }}
                      disabled={shiftingDate}
                      className="rounded-lg bg-green-600 px-3 py-1 text-sm font-semibold text-white transition hover:bg-green-700 disabled:opacity-50"
                    >
                      Да
                    </button>
                    <button
                      type="button"
                      onClick={() => setShiftConfirm(null)}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      Нет
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShiftConfirm(-1)}
                      disabled={shiftingDate}
                      className="flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-green-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      aria-label="Переместить на день назад"
                    >
                      <ChevronLeft className="h-5 w-5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setShiftConfirm(1)}
                      disabled={shiftingDate}
                      className="flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-green-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      aria-label="Переместить на день вперёд"
                    >
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </div>
                )
              ) : null}

              {onDelete ? (
                deleteConfirm ? (
                  <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5">
                    <span className="flex-1 text-sm font-medium text-red-700">Удалить приём пищи?</span>
                    <button
                      type="button"
                      onClick={() => {
                        setDeleteConfirm(false);
                        onDelete();
                      }}
                      disabled={deleting}
                      className="rounded-lg bg-red-600 px-3 py-1 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
                    >
                      Да
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteConfirm(false)}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      Нет
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setDeleteConfirm(true)}
                    disabled={deleting}
                    className="w-full rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
                  >
                    Удалить
                  </button>
                )
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {lightboxOpen && large ? (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/90"
          role="dialog"
          aria-modal="true"
          aria-label="Просмотр фото"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setLightboxOpen(false);
          }}
        >
          <button
            type="button"
            onClick={() => setLightboxOpen(false)}
            className="absolute right-3 top-3 rounded-full bg-white/10 p-2 text-white transition hover:bg-white/25"
            aria-label="Закрыть"
          >
            <X className="h-6 w-6" />
          </button>
          <img
            src={large}
            alt=""
            className="max-h-screen max-w-full cursor-zoom-out object-contain p-2"
            onClick={() => setLightboxOpen(false)}
          />
        </div>
      ) : null}
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
  /** Увеличивается после сохранения приёма из модалки — перезагрузка списка за выбранный день. */
  refreshToken?: number;
  readonly?: boolean;
  getMealsForDay?: (accessToken: string, dateYmd: string) => Promise<WebMealsDayResponse>;
  getNutritionTargetForDay?: (accessToken: string, dateYmd: string) => Promise<MyNutritionTargetEnvelope>;
}

export function MealHistoryDaySection({
  accessToken,
  nutritionTarget,
  onMealsChanged,
  onAddMealForDay,
  refreshToken = 0,
  readonly = false,
  getMealsForDay = getMyMealsForDay,
  getNutritionTargetForDay = getMyNutritionTarget,
}: MealHistoryDaySectionProps) {
  const [day, setDay] = useState(() => formatLocalYmd(new Date()));
  const [items, setItems] = useState<WebMealDayRow[]>([]);
  const [dayNutritionTarget, setDayNutritionTarget] = useState<NutritionTarget | null>(nutritionTarget);
  const [phase, setPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<WebMealDayRow | null>(null);
  const [editingMeal, setEditingMeal] = useState<WebMealDayRow | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [shiftingMealId, setShiftingMealId] = useState<number | null>(null);
  const [additiveTotals, setAdditiveTotals] = useState<DayNutritionTotals>(zeroDayNutritionTotals);
  const [additiveModalOpen, setAdditiveModalOpen] = useState(false);

  const load = useCallback(async () => {
    setPhase("loading");
    setError(null);
    try {
      const [mealsRes, targetRes] = await Promise.all([
        getMealsForDay(accessToken, day),
        getNutritionTargetForDay(accessToken, day),
      ]);
      setItems(mealsRes.items);
      setAdditiveTotals(mealsRes.additive_totals ?? zeroDayNutritionTotals());
      setDayNutritionTarget(targetRes.nutrition_target);
      setPhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить приёмы");
      setPhase("error");
    }
  }, [accessToken, day, getMealsForDay, getNutritionTargetForDay]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (refreshToken > 0) void load();
  }, [refreshToken, load]);

  const todayYmd = useMemo(() => formatLocalYmd(new Date()), []);
  const tomorrowYmd = useMemo(() => addDaysYmd(todayYmd, 1), [todayYmd]);
  const dateLabel = useMemo(() => ymdToRuLong(day), [day]);
  const dayGoals = useMemo(
    () => buildDayGoals(dayNutritionTarget, items, additiveTotals),
    [dayNutritionTarget, items, additiveTotals],
  );

  useEffect(() => {
    if (day > tomorrowYmd) setDay(tomorrowYmd);
  }, [day, tomorrowYmd]);

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

  const handleShiftDate = async (id: number, delta: 1 | -1) => {
    if (shiftingMealId != null) return;
    setShiftingMealId(id);
    try {
      await shiftMyMealDate(accessToken, id, delta);
      setDetail(null);
      await load();
      onMealsChanged?.();
    } finally {
      setShiftingMealId(null);
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
                max={tomorrowYmd}
                onChange={(e) => {
                  const v = e.target.value;
                  if (!v) return;
                  setDay(v > tomorrowYmd ? tomorrowYmd : v);
                }}
                className="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800"
              />
              <button
                type="button"
                onClick={() =>
                  setDay((d) => {
                    const next = addDaysYmd(d, 1);
                    return next > tomorrowYmd ? d : next;
                  })
                }
                disabled={day >= tomorrowYmd}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Следующий день"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
            {!readonly ? (
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                {onAddMealForDay ? (
                  <button
                    type="button"
                    onClick={() => onAddMealForDay(day)}
                    title="Добавить приём за выбранный день"
                    className="w-full rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-green-700 sm:flex-1"
                  >
                    + Прием пищи
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => setAdditiveModalOpen(true)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 sm:flex-1"
                >
                  Добавки
                </button>
              </div>
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
        {items.map((meal) =>
          readonly ? (
            <div
              key={meal.id}
              className="cursor-pointer border-b border-slate-100 last:border-b-0"
              onClick={() => setDetail(meal)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setDetail(meal);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <MealDayRowContent meal={meal} />
            </div>
          ) : (
            <SwipeMealRow
              key={meal.id}
              disabled={deletingId === meal.id}
              onDelete={() => void handleDelete(meal.id)}
              onOpen={() => setDetail(meal)}
            >
              <MealDayRowContent meal={meal} />
            </SwipeMealRow>
          ),
        )}
      </div>

      {detail ? (
        <MealDayDetailModal
          meal={detail}
          readonly={readonly}
          onClose={() => setDetail(null)}
          onEdit={() => {
            setEditingMeal(detail);
            setDetail(null);
          }}
          onShiftDate={!readonly ? (delta) => void handleShiftDate(detail.id, delta) : undefined}
          onDelete={!readonly ? () => void handleDelete(detail.id) : undefined}
          shiftingDate={shiftingMealId === detail.id}
          deleting={deletingId === detail.id}
        />
      ) : null}

      {!readonly ? (
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
      ) : null}

      <AdditiveIntakesDayModal
        open={additiveModalOpen}
        dateYmd={day}
        accessToken={accessToken}
        onClose={() => setAdditiveModalOpen(false)}
        onChanged={() => {
          void load();
          onMealsChanged?.();
        }}
      />
    </section>
  );
}
