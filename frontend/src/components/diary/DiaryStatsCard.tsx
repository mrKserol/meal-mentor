import { useEffect, useRef, useState } from "react";
import { BarChart3, X } from "lucide-react";

import type { DiarySnapshot } from "../../types/diary";
import {
  ANALYSIS_GROUPS,
  chartDayLabel,
  formatFixedRu,
  nutrientProfileFracDigits,
  nutrientProfileValue,
  type ChartDay,
} from "./diaryStatsUtils";

export interface DiaryStatsCardProps {
  snapshot: DiarySnapshot | null;
}

export function DiaryStatsCard({ snapshot }: DiaryStatsCardProps) {
  const statsChartScrollRef = useRef<HTMLDivElement | null>(null);
  const [statsPeriod, setStatsPeriod] = useState<"week" | "month">("week");
  const [analysisOpen, setAnalysisOpen] = useState(false);

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

  if (!snapshot) return null;

  return (
    <>
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
              <p className="text-xl font-bold text-orange-600">{formatFixedRu(activeStats?.avg_protein_g ?? 0, 0)} г</p>
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
              <p className="text-xl font-bold text-emerald-700">{formatFixedRu(activeStats?.avg_fiber_g ?? 0, 1)} г</p>
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
                Нутриентный профиль (средние суточные значения)
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
                        {item.label} -{" "}
                        {formatFixedRu(
                          nutrientProfileValue(activeStats, item.key),
                          nutrientProfileFracDigits(item.key),
                        )}{" "}
                        {item.unit}
                      </p>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
