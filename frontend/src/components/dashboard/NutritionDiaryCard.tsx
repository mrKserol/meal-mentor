import { BookOpen, Info } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { NutritionTarget } from "../../types/auth";
import type { DiaryTodayTotals } from "../../types/diary";

import { CircularMacroProgress } from "./CircularMacroProgress";

interface NutritionDiaryCardProps {
  nutritionTarget: NutritionTarget | null;
  /** Фактические КБЖУ за сегодня из дневника (`GET /users/me/diary`). */
  todayTotals: DiaryTodayTotals | null;
}

const ZERO_TODAY: DiaryTodayTotals = { calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0 };

export function NutritionDiaryCard({ nutritionTarget, todayTotals }: NutritionDiaryCardProps) {
  const navigate = useNavigate();
  const today = new Intl.DateTimeFormat("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());

  if (!nutritionTarget) {
    return (
      <div className="rounded-xl border border-outline-variant bg-white p-6 shadow-sm">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-container/25 text-primary">
              <BookOpen className="h-6 w-6" aria-hidden />
            </div>
            <h3 className="font-h2 text-h2 text-on-surface">Дневник питания</h3>
          </div>
          <span className="capitalize font-label-sm text-label-sm text-on-surface-variant">{today}</span>
        </div>
        <div className="rounded-xl border border-dashed border-outline-variant bg-surface-container-low p-8 text-center">
          <p className="font-h3 text-h3 text-on-surface">Дневная цель не рассчитана</p>
          <p className="mt-2 text-body-md text-on-surface-variant">
            Заполните профиль, чтобы рассчитать калории и БЖУ.
          </p>
          <button
            type="button"
            onClick={() => navigate("/onboarding/profile")}
            className="mt-5 inline-flex rounded-lg bg-primary px-5 py-2.5 font-bold text-on-primary hover:opacity-90"
          >
            Заполнить профиль
          </button>
        </div>
      </div>
    );
  }

  const calTarget = nutritionTarget.target_calories;
  const t = todayTotals ?? ZERO_TODAY;

  return (
    <div className="rounded-xl border border-outline-variant bg-white p-6 shadow-sm">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-container/25 text-primary">
            <BookOpen className="h-6 w-6" aria-hidden />
          </div>
          <h3 className="font-h2 text-h2 text-on-surface">Дневник питания</h3>
        </div>
        <span className="capitalize font-label-sm text-label-sm text-on-surface-variant">{today}</span>
      </div>

      <div className="mb-6 rounded-xl bg-surface-container-low px-5 py-4">
        <p className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Калории</p>
        <p className="mt-1 font-h3 text-h3 text-on-surface">
          {t.calories} kcal / {calTarget} kcal
        </p>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <CircularMacroProgress
          label="Белки"
          current={t.protein_g}
          target={nutritionTarget.target_protein_g}
          unit="g"
          ringClass="text-primary"
        />
        <CircularMacroProgress
          label="Углеводы"
          current={t.carbs_g}
          target={nutritionTarget.target_carbs_g}
          unit="g"
          ringClass="text-tertiary"
        />
        <CircularMacroProgress
          label="Жиры"
          current={t.fat_g}
          target={nutritionTarget.target_fat_g}
          unit="g"
          ringClass="text-secondary"
        />
      </div>

      <div className="flex items-start gap-3 rounded-xl bg-surface-container p-4">
        <Info className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden />
        <p className="text-body-md text-on-surface-variant">
          Съедено за сегодня по данным из дневника (сохранённые приёмы пищи). Добавить запись можно на странице{" "}
          <button
            type="button"
            onClick={() => navigate("/diary")}
            className="font-semibold text-primary underline hover:opacity-90"
          >
            Дневник
          </button>
          .
        </p>
      </div>
    </div>
  );
}
