import axios from "axios";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  FileUp,
  Loader2,
  PenLine,
  UtensilsCrossed,
  X,
} from "lucide-react";

import { analyzeMealImageBase64, analyzeMealText, saveMyMealToDiary } from "../../api/mealsApi";
import { useAuth } from "../../hooks/useAuth";
import {
  fileToBase64,
  formatMealAnalyzedDetail,
  formatRecognitionQuestion,
  needsUserDescription,
  parseAnalyzeResponse,
  type MealNutrition,
} from "../../utils/mealFlow";

type MealData = {
  ingredients: Record<string, string | number>;
  confidence: number | null;
  nutrition: MealNutrition | null;
  source_type: string;
  telegram_file_id: string | null;
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

export function AddMealModal({ open, onClose, onMealSaved }: AddMealModalProps) {
  const { validateSession, getAccessToken } = useAuth();
  const [ui, setUi] = useState<UiState>({ kind: "menu" });
  const [textDraft, setTextDraft] = useState("");
  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setUi({ kind: "menu" });
    setTextDraft("");
  }, []);

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
      const raw = await analyzeMealImageBase64(b64);
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "error", message: parsed.error || "Не удалось разобрать еду на фото." });
        return;
      }
      const { ingredients, confidence, nutrition } = parsed;
      if (needsUserDescription(ingredients, confidence)) {
        setUi({
          kind: "text",
          mode: "after_photo",
          hint: "Распознавание неуверенное. Опиши блюдо текстом — что на фото и примерные порции.",
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
    setUi({ kind: "busy", message: "Анализирую описание…" });
    try {
      const raw = await analyzeMealText(trimmed);
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "error", message: parsed.error || "Ошибка анализа текста." });
        return;
      }
      const { ingredients, confidence, nutrition } = parsed;
      if (needsUserDescription(ingredients, confidence)) {
        setUi({
          kind: "text",
          mode,
          hint:
            mode === "after_photo"
              ? "Не получилось выделить еду. Переформулируй подробнее (продукты и граммы)."
              : "По описанию мало данных. Добавь деталей: что именно и сколько примерно по весу.",
        });
        return;
      }
      const mealData: MealData = {
        ingredients,
        confidence,
        nutrition,
        source_type: mode === "after_photo" ? "text" : "text",
        telegram_file_id: null,
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
                Сфотографируйте еду, загрузите снимок или опишите блюдо текстом — как в Telegram-команде add_meal.
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
              <div className="flex justify-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-50 text-green-700">
                  <UtensilsCrossed className="h-7 w-7" aria-hidden />
                </div>
              </div>
              <p className="whitespace-pre-wrap text-center text-sm leading-relaxed text-slate-800">
                {formatRecognitionQuestion(ui.mealData.ingredients)}
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
                    setUi({ kind: "text", mode: "after_photo", hint: "Опиши блюдо текстом: что на фото и примерные порции." });
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
              <pre className="whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
                {formatMealAnalyzedDetail(ui.mealData.ingredients, ui.mealData.nutrition)}
              </pre>
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
