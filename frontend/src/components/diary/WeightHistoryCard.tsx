import { Plus, Scale } from "lucide-react";

import type { WeightMeasurementPeriod, WeightMeasurementPoint } from "../../types/diary";
import { formatFixedRu } from "./diaryStatsUtils";

const WEIGHT_PERIOD_OPTIONS: { value: WeightMeasurementPeriod; label: string }[] = [
  { value: "1m", label: "1 м" },
  { value: "3m", label: "3 м" },
  { value: "6m", label: "6 м" },
  { value: "1y", label: "1 г" },
  { value: "all", label: "Всё время" },
];

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

export interface WeightHistoryCardProps {
  weightKg: number | null;
  items: WeightMeasurementPoint[];
  phase: "idle" | "loading" | "ready" | "error";
  error: string | null;
  period: WeightMeasurementPeriod;
  onPeriodChange: (period: WeightMeasurementPeriod) => void;
  readonly?: boolean;
  onAddWeight?: () => void;
}

export function WeightHistoryCard({
  weightKg,
  items,
  phase,
  error,
  period,
  onPeriodChange,
  readonly = false,
  onAddWeight,
}: WeightHistoryCardProps) {
  return (
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
            onClick={() => onPeriodChange(item.value)}
            className={
              period === item.value
                ? "rounded-full bg-green-100 px-3 py-1 font-medium text-green-700"
                : "rounded-full px-3 py-1 font-medium text-slate-400 transition hover:bg-slate-100"
            }
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="py-4">
        {phase === "error" && error ? (
          <div className="flex h-36 items-center justify-center rounded-lg bg-red-50 px-4 text-center text-sm text-red-600">
            {error}
          </div>
        ) : phase === "loading" && items.length === 0 ? (
          <div className="flex h-36 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
            Загружаем взвешивания…
          </div>
        ) : (
          <WeightTrendChart items={items} />
        )}
      </div>

      {!readonly && onAddWeight ? (
        <div>
          <button
            type="button"
            onClick={onAddWeight}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700 sm:w-auto"
          >
            <Plus className="h-4 w-4" aria-hidden />
            Добавить взвешивание
          </button>
        </div>
      ) : null}
    </section>
  );
}
