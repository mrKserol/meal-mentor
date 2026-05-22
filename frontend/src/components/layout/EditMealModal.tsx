import { useCallback, useEffect, useState } from "react";
import { X } from "lucide-react";

import { updateMyMeal } from "../../api/diaryApi";
import { MealCompositionForm } from "../meals/MealCompositionForm";
import { webMealRowToComposition, type MealCompositionState } from "../../utils/mealFlow";
import type { WebMealDayRow } from "../../types/mealsDay";

type EditMealModalProps = {
  open: boolean;
  meal: WebMealDayRow | null;
  accessToken: string;
  onClose: () => void;
  onSaved?: () => void;
};

export function EditMealModal({ open, meal, accessToken, onClose, onSaved }: EditMealModalProps) {
  const [mealData, setMealData] = useState<MealCompositionState | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && meal) {
      setMealData(webMealRowToComposition(meal));
      setError(null);
    }
    if (!open) {
      setMealData(null);
      setSaving(false);
      setError(null);
    }
  }, [open, meal]);

  const handleSave = useCallback(async () => {
    if (!meal || !mealData) return;
    if (!Object.keys(mealData.ingredients).length) {
      setError("Добавьте хотя бы один ингредиент.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateMyMeal(accessToken, meal.id, {
        ingredients: mealData.ingredients,
        prediction: mealData.prediction,
        prediction_translated: mealData.prediction_translated ?? null,
        prediction_language: mealData.prediction_language ?? null,
      });
      onSaved?.();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить изменения.");
    } finally {
      setSaving(false);
    }
  }, [meal, mealData, accessToken, onClose, onSaved]);

  if (!open || !meal || !mealData) return null;

  return (
    <div
      className="fixed inset-0 z-[110] flex items-end justify-center bg-black/45 p-4 sm:items-center"
      role="presentation"
      onMouseDown={(ev) => {
        if (ev.target === ev.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-meal-title"
        className="flex max-h-[min(92vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 id="edit-meal-title" className="text-lg font-semibold text-slate-900">
            Изменение приема пищи
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100"
            aria-label="Закрыть"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
          <MealCompositionForm
            mealData={mealData}
            onMealDataChange={setMealData}
            accessToken={accessToken}
            savePrompt="Сохранить изменения в приеме пищи?"
            primaryLabel={saving ? "Сохраняю…" : "Да, сохранить"}
            secondaryLabel="Отмена"
            onPrimary={() => void handleSave()}
            onSecondary={onClose}
            primaryDisabled={saving}
          />
        </div>
      </div>
    </div>
  );
}
