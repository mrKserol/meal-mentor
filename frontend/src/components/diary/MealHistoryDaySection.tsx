import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Apple, ChevronLeft, ChevronRight, Coffee, Salad, X } from "lucide-react";

import { deleteMyMeal, getMyMealsForDay } from "../../api/diaryApi";
import type { WebMealDayRow } from "../../types/mealsDay";
import { formatIntRu } from "../../utils/recentMeals";

const DELETE_PANEL_PX = 96;

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

function MealDayDetailModal({
  meal,
  onClose,
}: {
  meal: WebMealDayRow;
  onClose: () => void;
}) {
  const large = meal.meal_photo_large_url || meal.meal_photo_thumb_url;
  const pred = predictionHeading(meal);

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
          <p className="text-sm text-slate-600">
            Приём пищи в {meal.time_local}
            {meal.meal_type_label ? ` · ${meal.meal_type_label}` : ""}
          </p>
          <p className="text-sm leading-relaxed text-slate-800">
            <span className="font-medium text-slate-900">Состав:</span> {meal.composition}
          </p>
          <p className="text-sm font-semibold text-slate-900">{formatIntRu(meal.calories)} kcal</p>
          {meal.items.length > 0 ? (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100 text-sm">
              {meal.items.map((it) => (
                <li key={it.id} className="flex flex-wrap items-baseline justify-between gap-2 px-3 py-2">
                  <span className="text-slate-800">
                    {it.item_name || "—"}
                    {it.estimated_weight_g != null ? ` · ${it.estimated_weight_g} г` : ""}
                  </span>
                  <span className="shrink-0 text-slate-500">
                    {it.calories != null ? `${formatIntRu(it.calories)} kcal` : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function MealDayRowContent({ meal }: { meal: WebMealDayRow }) {
  const thumb = meal.meal_photo_thumb_url;
  const pred = predictionHeading(meal);

  return (
    <div className="flex w-full items-start gap-3 p-4 text-left transition hover:bg-slate-50 md:p-5">
      <div className="flex w-14 shrink-0 flex-col items-end pt-0.5">
        <span className="text-base font-bold leading-none text-slate-900">{formatIntRu(meal.calories)}</span>
        <span className="mt-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">kcal</span>
      </div>
      {thumb ? (
        <img src={thumb} alt="" className="h-16 w-16 shrink-0 rounded-xl object-cover" loading="lazy" />
      ) : (
        <MealIconCard mealType={meal.meal_type} />
      )}
      <div className="min-w-0 flex-1">
        <h3 className="text-base font-semibold leading-snug text-slate-900">{pred}</h3>
        <p className="mt-1 text-sm text-slate-600">Приём пищи в {meal.time_local}</p>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">
          <span className="font-medium text-slate-800">Состав:</span> {meal.composition}
        </p>
      </div>
    </div>
  );
}

interface MealHistoryDaySectionProps {
  accessToken: string;
  onMealsChanged?: () => void;
}

export function MealHistoryDaySection({ accessToken, onMealsChanged }: MealHistoryDaySectionProps) {
  const [day, setDay] = useState(() => formatLocalYmd(new Date()));
  const [items, setItems] = useState<WebMealDayRow[]>([]);
  const [phase, setPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<WebMealDayRow | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setPhase("loading");
    setError(null);
    try {
      const res = await getMyMealsForDay(accessToken, day);
      setItems(res.items);
      setPhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить приёмы");
      setPhase("error");
    }
  }, [accessToken, day]);

  useEffect(() => {
    void load();
  }, [load]);

  const dateLabel = useMemo(() => ymdToRuLong(day), [day]);

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
        <h2 className="text-xl font-semibold text-slate-900">История приёмов пищи</h2>
        <p className="mt-1 text-sm capitalize text-slate-500">{dateLabel}</p>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 sm:justify-between">
          <div className="flex items-center gap-1">
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
              onChange={(e) => {
                const v = e.target.value;
                if (v) setDay(v);
              }}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800"
            />
            <button
              type="button"
              onClick={() => setDay((d) => addDaysYmd(d, 1))}
              className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50"
              aria-label="Следующий день"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
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

      {detail ? <MealDayDetailModal meal={detail} onClose={() => setDetail(null)} /> : null}
    </section>
  );
}
