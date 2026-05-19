import axios from "axios";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  CircleMinus,
  FileUp,
  Loader2,
  PenLine,
  Plus,
  X,
} from "lucide-react";

import {
  analyzeMealImageBase64,
  analyzeMealImageWithText,
  analyzeMealText,
  recalculateMealNutrition,
  saveMyMealToDiary,
} from "../../api/mealsApi";
import { useAuth } from "../../hooks/useAuth";
import {
  fileToBase64,
  formatRecognitionQuestion,
  ingredientGramsLabel,
  needsUserDescription,
  parseAnalyzeResponse,
  type IngredientEntry,
  type MealNutrition,
} from "../../utils/mealFlow";

type MealData = {
  ingredients: Record<string, IngredientEntry>;
  confidence: number | null;
  nutrition: MealNutrition | null;
  source_type: string;
  telegram_file_id: string | null;
  prediction: string | null;
  user_text?: string | null;
  image_base64?: string | null;
};

type UiState =
  | { kind: "menu" }
  | { kind: "busy"; message: string }
  | {
      kind: "recognition";
      mealData: MealData;
    }
  | { kind: "text"; mode: "standalone" | "after_photo"; hint?: string }
  | { kind: "confirm"; mealData: MealData }
  | { kind: "error"; message: string };

interface AddMealModalProps {
  open: boolean;
  onClose: () => void;
  onMealSaved?: () => void;
}

function MealPhotoPreview({ imageBase64 }: { imageBase64?: string | null }) {
  if (!imageBase64) return null;

  return (
    <img
      src={`data:image/jpeg;base64,${imageBase64}`}
      alt="Фото блюда"
      className="max-h-64 w-full rounded-xl object-cover"
    />
  );
}

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

export function AddMealModal({ open, onClose, onMealSaved }: AddMealModalProps) {
  const { validateSession, getAccessToken } = useAuth();
  const [ui, setUi] = useState<UiState>({ kind: "menu" });
  const [textDraft, setTextDraft] = useState("");
  const [showAddIngredient, setShowAddIngredient] = useState(false);
  const [newIngredientText, setNewIngredientText] = useState("");
  const [addIngredientError, setAddIngredientError] = useState<string | null>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const photoB64Ref = useRef<string | null>(null);

  const reset = useCallback(() => {
    setUi({ kind: "menu" });
    setTextDraft("");
    setShowAddIngredient(false);
    setNewIngredientText("");
    setAddIngredientError(null);
    photoB64Ref.current = null;
  }, []);

  const updateConfirmMealData = useCallback((updater: (mealData: MealData) => MealData) => {
    setUi((prev) => {
      if (prev.kind !== "confirm") return prev;
      return { kind: "confirm", mealData: updater(prev.mealData) };
    });
  }, []);

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

        updateConfirmMealData((mealData) => ({
          ...mealData,
          ingredients: nextIngredients,
          nutrition: parsed.nutrition,
        }));
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Не удалось пересчитать БЖУ.";
        if (options?.onError) {
          options.onError(message);
        } else {
          setUi({ kind: "error", message });
        }
        return false;
      }
    },
    [updateConfirmMealData],
  );

  const recalcCurrentMealNutrition = useCallback(async () => {
    if (ui.kind !== "confirm") return;
    await recalcNutritionForIngredients(ui.mealData.ingredients);
  }, [ui, recalcNutritionForIngredients]);

  const updateIngredientWeight = useCallback(
    (name: string, value: string) => {
      updateConfirmMealData((mealData) => ({
        ...mealData,
        ingredients: {
          ...mealData.ingredients,
          [name]: Number(value) || 0,
        },
      }));
    },
    [updateConfirmMealData],
  );

  const removeIngredient = useCallback(
    (name: string) => {
      if (ui.kind !== "confirm") return;
      const nextIngredients = { ...ui.mealData.ingredients };
      delete nextIngredients[name];
      void recalcNutritionForIngredients(nextIngredients);
    },
    [ui, recalcNutritionForIngredients],
  );

  const addIngredientFromText = async () => {
    const parsed = parseIngredientName(newIngredientText);
    if (!parsed) {
      setAddIngredientError("Введите название ингредиента");
      return;
    }

    if (ui.kind !== "confirm") return;

    const nextIngredients = {
      ...ui.mealData.ingredients,
      [parsed.name]: parsed.grams,
    };

    const ok = await recalcNutritionForIngredients(nextIngredients, {
      onError: (message) => setAddIngredientError(message),
    });
    if (!ok) return;

    setAddIngredientError(null);
    setNewIngredientText("");
    setShowAddIngredient(false);
  };

  useEffect(() => {
    if (open) reset();
  }, [open, reset]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const runAnalyzeImage = async (file: File) => {
    setUi({ kind: "busy", message: "Анализирую фото…" });
    try {
      const b64 = await fileToBase64(file);
      photoB64Ref.current = b64;
      const raw = await analyzeMealImageBase64(b64);
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "error", message: parsed.error || "Не удалось разобрать еду на фото." });
        return;
      }
      const { ingredients, confidence, nutrition, prediction } = parsed;
      if (needsUserDescription(ingredients, confidence)) {
        setUi({
          kind: "text",
          mode: "after_photo",
          hint: "Распознавание неуверенное. Опиши блюдо на фото и примерные порции.",
        });
        return;
      }
      setUi({
        kind: "recognition",
        mealData: {
          ingredients,
          confidence,
          nutrition,
          source_type: "photo",
          telegram_file_id: null,
          prediction,
          image_base64: b64,
        },
      });
    } catch (err) {
      setUi({
        kind: "error",
        message: axios.isAxiosError(err) ? String(err.response?.data?.detail ?? err.message) : "Ошибка сети.",
      });
    }
  };

  const runAnalyzeText = async (text: string, mode: "standalone" | "after_photo") => {
    const trimmed = text.trim();
    if (!trimmed) {
      setUi({ kind: "error", message: "Введите описание блюда." });
      return;
    }
    setUi({
      kind: "busy",
      message: mode === "after_photo" ? "Анализирую фото и описание…" : "Анализирую описание…",
    });
    try {
      const raw =
        mode === "after_photo" && photoB64Ref.current
          ? await analyzeMealImageWithText(photoB64Ref.current, trimmed)
          : await analyzeMealText(trimmed);
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "error", message: parsed.error || "Ошибка анализа текста." });
        return;
      }
      const { ingredients, confidence, nutrition, prediction } = parsed;
      if (needsUserDescription(ingredients, confidence)) {
        setUi({
          kind: "text",
          mode,
          hint:
            mode === "after_photo"
              ? "Не получилось выделить еду. Уточни подробнее: что на фото и примерные порции."
              : "По описанию мало данных. Добавь деталей: что именно и сколько примерно по весу.",
        });
        return;
      }
      const mealData: MealData = {
        ingredients,
        confidence,
        nutrition,
        source_type: mode === "after_photo" ? "photo_text" : "text",
        telegram_file_id: null,
        prediction,
        user_text: trimmed,
        ...(mode === "after_photo" && photoB64Ref.current
          ? { image_base64: photoB64Ref.current }
          : {}),
      };
      if (mode === "after_photo") {
        setUi({ kind: "confirm", mealData });
      } else {
        setUi({ kind: "recognition", mealData });
      }
    } catch (err) {
      setUi({
        kind: "error",
        message: axios.isAxiosError(err) ? String(err.response?.data?.detail ?? err.message) : "Ошибка сети.",
      });
    }
  };

  const onImageSelected = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    void runAnalyzeImage(f);
  };

  const confirmSave = async () => {
    if (ui.kind !== "confirm") return;
    setUi({ kind: "busy", message: "Сохраняю в дневник…" });
    try {
      const ok = await validateSession();
      if (!ok) throw new Error("Сессия истекла.");
      const token = getAccessToken();
      if (!token) throw new Error("Нет авторизации.");
      await saveMyMealToDiary(token, {
        ingredients: ui.mealData.ingredients,
        source_type: ui.mealData.source_type,
        telegram_file_id: ui.mealData.telegram_file_id,
        prediction: ui.mealData.prediction,
        user_text: ui.mealData.user_text ?? undefined,
        image_base64: ui.mealData.image_base64 ?? undefined,
      });
      onMealSaved?.();
      setUi({ kind: "menu" });
      onClose();
    } catch (err) {
      setUi({
        kind: "error",
        message: err instanceof Error ? err.message : "Не удалось сохранить.",
      });
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/45 p-4 sm:items-center"
      role="presentation"
      onMouseDown={(ev) => {
        if (ev.target === ev.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-meal-title"
        className="flex max-h-[min(92vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 id="add-meal-title" className="text-lg font-semibold text-slate-900">
            Добавить прием пищи
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
          {ui.kind === "menu" ? (
            <div className="space-y-4">
              <p className="text-center text-sm text-slate-600">
                Сфотографируйте еду, загрузите снимок или опишите блюдо текстом
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => cameraRef.current?.click()}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-green-600 bg-green-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700"
                >
                  <Camera className="h-5 w-5 shrink-0" aria-hidden />
                  Сфотографировать
                </button>
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-green-200 hover:bg-green-50/50"
                >
                  <FileUp className="h-5 w-5 shrink-0" aria-hidden />
                  Загрузить файл
                </button>
              </div>
              <button
                type="button"
                onClick={() => {
                  setTextDraft("");
                  photoB64Ref.current = null;
                  setUi({ kind: "text", mode: "standalone" });
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-100"
              >
                <PenLine className="h-5 w-5 shrink-0" aria-hidden />
                Написать текстом
              </button>
              <input
                ref={cameraRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/*"
                capture="environment"
                className="sr-only"
                onChange={onImageSelected}
              />
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/*"
                className="sr-only"
                onChange={onImageSelected}
              />
            </div>
          ) : null}

          {ui.kind === "busy" ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-slate-600">
              <Loader2 className="h-10 w-10 animate-spin text-green-600" aria-hidden />
              <p className="text-sm font-medium">{ui.message}</p>
            </div>
          ) : null}

          {ui.kind === "recognition" ? (
            <div className="space-y-4">
              <MealPhotoPreview imageBase64={ui.mealData.image_base64} />
              <p className="whitespace-pre-wrap text-center text-sm leading-relaxed text-slate-800">
                {formatRecognitionQuestion(ui.mealData.ingredients, ui.mealData.prediction)}
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() =>
                    setUi({
                      kind: "confirm",
                      mealData: ui.mealData,
                    })
                  }
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
                >
                  Да, верно
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTextDraft("");
                    setUi({ kind: "text", mode: "after_photo", hint: "Опиши блюдо на фото и примерные порции." });
                  }}
                  className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
                >
                  Нет, напишу вручную
                </button>
              </div>
            </div>
          ) : null}

          {ui.kind === "text" ? (
            <div className="space-y-3">
              {ui.mode === "after_photo" ? (
                <MealPhotoPreview imageBase64={photoB64Ref.current} />
              ) : null}
              {ui.hint ? <p className="text-sm text-slate-600">{ui.hint}</p> : null}
              <label className="block text-sm font-medium text-slate-700">Описание блюда</label>
              <textarea
                value={textDraft}
                onChange={(e) => setTextDraft(e.target.value)}
                rows={5}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none ring-green-100 focus:border-green-600 focus:ring-2"
                placeholder="Например: гречка с курицей 300 г, салат из огурцов 150 г"
              />
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => void runAnalyzeText(textDraft, ui.mode)}
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
                >
                  Анализировать
                </button>
                <button
                  type="button"
                  onClick={reset}
                  className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Назад
                </button>
              </div>
            </div>
          ) : null}

          {ui.kind === "confirm" ? (
            <div className="space-y-4">
              <MealPhotoPreview imageBase64={ui.mealData.image_base64} />

              {ui.mealData.prediction ? (
                <p className="text-sm font-semibold text-slate-900">{ui.mealData.prediction}</p>
              ) : null}

              <p className="text-sm font-semibold text-slate-900">Состав и вес (г):</p>

              <div className="space-y-2">
                {Object.entries(ui.mealData.ingredients).map(([name, entry]) => (
                  <div
                    key={name}
                    className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
                  >
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-800">{name}</span>

                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={ingredientGramsLabel(entry)}
                      onChange={(e) => updateIngredientWeight(name, e.target.value)}
                      onBlur={() => void recalcCurrentMealNutrition()}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.currentTarget.blur();
                        }
                      }}
                      className="w-20 rounded-lg border border-slate-200 bg-white px-2 py-1 text-right text-sm outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
                    />

                    <button
                      type="button"
                      onClick={() => removeIngredient(name)}
                      className="rounded-lg p-2 text-red-600 transition hover:bg-red-50"
                      aria-label={`Удалить ${name}`}
                    >
                      <CircleMinus className="h-5 w-5" aria-hidden />
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => {
                  setAddIngredientError(null);
                  setShowAddIngredient(true);
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                <Plus className="h-4 w-4" aria-hidden />
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
                  {addIngredientError ? (
                    <p className="text-sm text-red-600">{addIngredientError}</p>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => void addIngredientFromText()}
                    className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
                  >
                    Добавить
                  </button>
                </div>
              ) : null}

              {ui.mealData.nutrition ? (
                <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-800">
                  <p className="font-semibold">БЖУ (оценка):</p>
                  <p>
                    Калории: {ui.mealData.nutrition.calories} ккал | Б: {ui.mealData.nutrition.proteins} г | Ж:{" "}
                    {ui.mealData.nutrition.fats} г | У: {ui.mealData.nutrition.carbohydrates} г
                  </p>
                </div>
              ) : null}

              <p className="text-sm font-medium text-slate-700">Записать прием пищи в дневник?</p>

              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => void confirmSave()}
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
                >
                  Да, записать
                </button>
                <button
                  type="button"
                  onClick={() => {
                    reset();
                    onClose();
                  }}
                  className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : null}

          {ui.kind === "error" ? (
            <div className="space-y-4">
              <p className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-800">{ui.message}</p>
              <button
                type="button"
                onClick={reset}
                className="w-full rounded-xl bg-slate-100 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-200"
              >
                Начать сначала
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
