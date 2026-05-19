import { useCallback, useEffect, useRef, useState } from "react";
import { CircleMinus, Minus, Plus } from "lucide-react";

import { recalculateMealNutrition } from "../../api/mealsApi";
import {
  ingredientGramsLabel,
  parseAnalyzeResponse,
  setIngredientGrams,
  type IngredientEntry,
  type MealCompositionState,
} from "../../utils/mealFlow";
import { EditableMealTitle } from "./EditableMealTitle";
import { MealPhotoPreview } from "./MealPhotoPreview";

function parseIngredientName(input: string): { name: string; grams: number } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  const withWeight = trimmed.match(/^(.+?)\s+(\d+(?:[.,]\d+)?)$/);
  if (withWeight) {
    const name = withWeight[1].trim();
    const grams = Math.round(Number(withWeight[2].replace(",", ".")));
    if (!name || !Number.isFinite(grams) || grams < 0) return null;
    return { name, grams };
  }

  return { name: trimmed, grams: 0 };
}

type MealCompositionFormProps = {
  mealData: MealCompositionState;
  onMealDataChange: (data: MealCompositionState) => void;
  savePrompt: string;
  primaryLabel: string;
  secondaryLabel: string;
  onPrimary: () => void;
  onSecondary: () => void;
  primaryDisabled?: boolean;
};

export function MealCompositionForm({
  mealData,
  onMealDataChange,
  savePrompt,
  primaryLabel,
  secondaryLabel,
  onPrimary,
  onSecondary,
  primaryDisabled,
}: MealCompositionFormProps) {
  const [showAddIngredient, setShowAddIngredient] = useState(false);
  const [newIngredientText, setNewIngredientText] = useState("");
  const [addIngredientError, setAddIngredientError] = useState<string | null>(null);
  const addIngredientRef = useRef<HTMLDivElement>(null);

  const recalcNutritionForIngredients = useCallback(
    async (
      nextIngredients: Record<string, IngredientEntry>,
      options?: { onError?: (message: string) => void },
    ) => {
      try {
        const raw = await recalculateMealNutrition(nextIngredients);
        const parsed = parseAnalyzeResponse(raw);
        if (parsed.status !== "success") {
          throw new Error(parsed.error || "Не удалось пересчитать БЖУ.");
        }
        onMealDataChange({
          ...mealData,
          ingredients: nextIngredients,
          nutrition: parsed.nutrition,
        });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Не удалось пересчитать БЖУ.";
        options?.onError?.(message);
        return false;
      }
    },
    [mealData, onMealDataChange],
  );

  const recalcCurrentMealNutrition = useCallback(async () => {
    await recalcNutritionForIngredients(mealData.ingredients);
  }, [mealData.ingredients, recalcNutritionForIngredients]);

  const closeAddIngredientPanel = useCallback((clearDraft: boolean) => {
    setShowAddIngredient(false);
    setAddIngredientError(null);
    if (clearDraft) setNewIngredientText("");
  }, []);

  const toggleAddIngredient = () => {
    if (showAddIngredient) {
      closeAddIngredientPanel(!newIngredientText.trim());
    } else {
      setAddIngredientError(null);
      setShowAddIngredient(true);
    }
  };

  useEffect(() => {
    if (!showAddIngredient) return;

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (addIngredientRef.current?.contains(target)) return;
      closeAddIngredientPanel(!newIngredientText.trim());
    };

    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [showAddIngredient, newIngredientText, closeAddIngredientPanel]);

  const addIngredientFromText = async () => {
    const parsed = parseIngredientName(newIngredientText);
    if (!parsed) {
      setAddIngredientError("Введите название ингредиента");
      return;
    }

    const nextIngredients = {
      ...mealData.ingredients,
      [parsed.name]: parsed.grams,
    };

    const ok = await recalcNutritionForIngredients(nextIngredients, {
      onError: (message) => setAddIngredientError(message),
    });
    if (!ok) return;

    closeAddIngredientPanel(true);
  };

  return (
    <div className="space-y-4">
      <MealPhotoPreview imageBase64={mealData.image_base64} imageUrl={mealData.image_url} />

      <EditableMealTitle
        value={mealData.prediction ?? ""}
        onChange={(prediction) => onMealDataChange({ ...mealData, prediction: prediction || null })}
      />

      <p className="text-sm font-semibold text-slate-900">Состав и вес (г):</p>

      <div className="space-y-2">
        {Object.entries(mealData.ingredients).map(([name, entry]) => (
          <div
            key={name}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
          >
            <span className="min-w-0 flex-1 truncate text-sm text-slate-800">{name}</span>
            <input
              type="number"
              min={0}
              step={1}
              value={ingredientGramsLabel(entry)}
              onChange={(e) =>
                onMealDataChange({
                  ...mealData,
                  ingredients: setIngredientGrams(
                    mealData.ingredients,
                    name,
                    Number(e.target.value) || 0,
                  ),
                })
              }
              onBlur={() => void recalcCurrentMealNutrition()}
              onKeyDown={(e) => {
                if (e.key === "Enter") e.currentTarget.blur();
              }}
              className="w-20 rounded-lg border border-slate-200 bg-white px-2 py-1 text-right text-sm outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
            />
            <button
              type="button"
              onClick={() => {
                const nextIngredients = { ...mealData.ingredients };
                delete nextIngredients[name];
                void recalcNutritionForIngredients(nextIngredients);
              }}
              className="rounded-lg p-2 text-red-600 transition hover:bg-red-50"
              aria-label={`Удалить ${name}`}
            >
              <CircleMinus className="h-5 w-5" aria-hidden />
            </button>
          </div>
        ))}
      </div>

      <div ref={addIngredientRef} className="space-y-2">
        <button
          type="button"
          onClick={toggleAddIngredient}
          aria-expanded={showAddIngredient}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          {showAddIngredient ? <Minus className="h-4 w-4" aria-hidden /> : <Plus className="h-4 w-4" aria-hidden />}
          Добавить ингредиент
        </button>
        {showAddIngredient ? (
          <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <input
              value={newIngredientText}
              onChange={(e) => {
                setNewIngredientText(e.target.value);
                if (addIngredientError) setAddIngredientError(null);
              }}
              placeholder="Например: potato"
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
            />
            {addIngredientError ? <p className="text-sm text-red-600">{addIngredientError}</p> : null}
            <button
              type="button"
              onClick={() => void addIngredientFromText()}
              className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
            >
              Добавить
            </button>
          </div>
        ) : null}
      </div>

      {mealData.nutrition ? (
        <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-800">
          <p className="font-semibold">БЖУ (оценка):</p>
          <p>
            Калории: {mealData.nutrition.calories} ккал | Б: {mealData.nutrition.proteins} г | Ж:{" "}
            {mealData.nutrition.fats} г | У: {mealData.nutrition.carbohydrates} г
          </p>
        </div>
      ) : null}

      <p className="text-sm font-medium text-slate-700">{savePrompt}</p>

      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={onPrimary}
          disabled={primaryDisabled}
          className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700 disabled:opacity-50"
        >
          {primaryLabel}
        </button>
        <button
          type="button"
          onClick={onSecondary}
          className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          {secondaryLabel}
        </button>
      </div>
    </div>
  );
}
