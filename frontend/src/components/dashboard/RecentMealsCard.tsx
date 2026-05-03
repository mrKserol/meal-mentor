import { Link } from "react-router-dom";
import { Apple, ChevronRight, Coffee, Salad } from "lucide-react";

import type { MealHistoryItem } from "../../utils/recentMeals";
import { formatIntRu } from "../../utils/recentMeals";

function getMealIcon(icon: MealHistoryItem["icon"]) {
  if (icon === "breakfast") return Coffee;
  if (icon === "lunch") return Salad;
  return Apple;
}

function MealIconCard({ icon }: { icon: MealHistoryItem["icon"] }) {
  const Icon = getMealIcon(icon);
  return (
    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
      <Icon className="h-7 w-7" aria-hidden />
    </div>
  );
}

interface RecentMealsCardProps {
  items: MealHistoryItem[];
}

export function RecentMealsCard({ items }: RecentMealsCardProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 p-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Приемы пищи сегодня</h2>
        </div>
        <Link
          to="/diary"
          className="flex items-center gap-1 text-sm font-bold text-green-700 transition hover:text-green-800"
        >
          Смотреть все
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>

      <div className="divide-y divide-slate-100">
        {items.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>Пока нет записей.</p>
            <Link
              to="/diary"
              className="mt-3 inline-block font-semibold text-green-700 underline hover:text-green-800"
            >
              Открыть дневник
            </Link>
          </div>
        ) : (
          items.map((meal) => (
            <div key={meal.id} className="flex items-start gap-3 p-4 transition hover:bg-slate-50 md:p-5">
              <div className="flex w-14 shrink-0 flex-col items-end pt-0.5">
                <span className="text-base font-bold leading-none text-slate-900">{formatIntRu(meal.calories)}</span>
                <span className="mt-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">kcal</span>
              </div>
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
                <p className="mt-1 text-sm text-slate-600">Приём пищи в {meal.time}</p>
                <p className="mt-2 text-sm leading-relaxed text-slate-700">
                  <span className="font-medium text-slate-800">Состав:</span> {meal.composition}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
