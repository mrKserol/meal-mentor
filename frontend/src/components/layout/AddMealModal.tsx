import axios from "axios";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Camera, FileUp, Loader2, PenLine, Pill, X } from "lucide-react";

import { recordWaterIntake } from "../../api/additivesApi";
import { WaterButton } from "../common/WaterButton";
import { TakeAdditiveModal } from "../additives/TakeAdditiveModal";

import {
  analyzeMealImageBase64,
  analyzeMealImageWithText,
  analyzeMealText,
  saveMyMealToDiary,
} from "../../api/mealsApi";
import { useAuth } from "../../hooks/useAuth";
import { MealCompositionForm } from "../meals/MealCompositionForm";
import { MealPhotoPreview } from "../meals/MealPhotoPreview";
import {
  fileToBase64,
  ingredientDisplayName,
  mealDisplayPrediction,
  parseAnalyzeResponse,
  type IngredientEntry,
  type MealCompositionState,
  type MealNutrition,
} from "../../utils/mealFlow";

type MealData = {
  ingredients: Record<string, IngredientEntry>;
  confidence: number | null;
  nutrition: MealNutrition | null;
  source_type: string;
  telegram_file_id: string | null;
  prediction: string | null;
  prediction_translated?: string | null;
  prediction_language?: string | null;
  user_text?: string | null;
  image_base64?: string | null;
};

type UiState =
  | { kind: "menu" }
  | { kind: "busy"; message: string }
  | { kind: "photo_preview" }
  | {
      kind: "recognition";
      mealData: MealData;
    }
  | {
      kind: "text";
      mode: "standalone" | "after_photo";
      hint?: string;
      previousMealData?: MealData | null;
    }
  | { kind: "confirm"; mealData: MealData }
  | { kind: "error"; message: string };

interface AddMealModalProps {
  open: boolean;
  onClose: () => void;
  onMealSaved?: () => void;
  /** YYYY-MM-DD: день записи из истории; время по умолчанию — текущее локальное. */
  mealLocalDate?: string | null;
}

type ScheduledLocal = { date: string; time: string };

function formatLocalYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function buildDefaultScheduled(dateYmd: string): ScheduledLocal {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, "0");
  const m = String(now.getMinutes()).padStart(2, "0");
  return { date: dateYmd, time: `${h}:${m}` };
}

function toMealLocalDatetime(scheduled: ScheduledLocal): string {
  return `${scheduled.date}T${scheduled.time}`;
}

function validateScheduled(scheduled: ScheduledLocal, tomorrowYmd: string): string | null {
  const [y, mo, da] = scheduled.date.split("-").map(Number);
  const [hh, mm] = scheduled.time.split(":").map(Number);
  const chosen = new Date(y, mo - 1, da, hh, mm);
  const [ty, tmo, tda] = tomorrowYmd.split("-").map(Number);
  const max = new Date(ty, tmo - 1, tda, 23, 59, 59, 999);
  if (chosen > max) {
    return "Дата и время не могут быть позже завтрашнего дня.";
  }
  return null;
}

function MealScheduledTimeBlock({
  scheduled,
  tomorrowYmd,
  onScheduledChange,
}: {
  scheduled: ScheduledLocal;
  tomorrowYmd: string;
  onScheduledChange: (next: ScheduledLocal) => void;
}) {
  return (
    <div className="space-y-2 rounded-xl border border-green-100 bg-green-50/70 p-3">
      <p className="text-center text-sm font-medium text-green-900">Прием будет записан</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_7.5rem] sm:items-center">
        <input
          type="date"
          value={scheduled.date}
          max={tomorrowYmd}
          onChange={(e) => {
            const v = e.target.value;
            if (!v) return;
            onScheduledChange({ ...scheduled, date: v > tomorrowYmd ? tomorrowYmd : v });
          }}
          className="box-border w-full min-w-0 max-w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
        />
        <div className="min-w-0 w-full max-w-full overflow-hidden">
          <input
            type="time"
            value={scheduled.time}
            onChange={(e) => onScheduledChange({ ...scheduled, time: e.target.value })}
            className="meal-time-input box-border w-full min-w-0 max-w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm sm:px-2.5"
          />
        </div>
      </div>
    </div>
  );
}

function mealIngredientsLine(mealData: MealData): string {
  const items = Object.entries(mealData.ingredients).map(([name, entry]) => ingredientDisplayName(name, entry));
  return items.length > 0 ? items.join(" • ") : "—";
}

function MealPredictionConfirmStep({
  mealData,
  onConfirm,
  onCorrection,
}: {
  mealData: MealData;
  onConfirm: () => void;
  onCorrection: () => void;
}) {
  const predictionTitle = mealDisplayPrediction(mealData) || "блюдо";

  return (
    <div className="space-y-4">
      <MealPhotoPreview imageBase64={mealData.image_base64} />
      <div className="space-y-3 text-center text-sm leading-relaxed text-slate-800">
        <p>
          Похоже, что это:{" "}
          <span className="text-[15px] font-bold leading-snug text-slate-900">{predictionTitle}</span>
        </p>
        <div>
          <p className="font-medium text-slate-900">Примерный состав:</p>
          <p className="mt-1">{mealIngredientsLine(mealData)}</p>
        </div>
        <p className="font-medium text-slate-900">Я верно определил?</p>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={onConfirm}
          className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
        >
          Да, верно
        </button>
        <button
          type="button"
          onClick={onCorrection}
          className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
        >
          Нет, коррекция
        </button>
      </div>
    </div>
  );
}

function MealCorrectionStep({
  imageBase64,
  value,
  onChange,
  onBack,
  onAnalyze,
  isAnalyzing,
  placeholder = "Например: это цикорий, не кофе; заправка йогуртовая, не майонез",
}: {
  imageBase64?: string | null;
  value: string;
  onChange: (value: string) => void;
  onBack: () => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
  placeholder?: string;
}) {
  return (
    <div className="space-y-3">
      <MealPhotoPreview imageBase64={imageBase64} />
      <label className="block text-sm font-medium text-slate-700">Описание блюда</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={5}
        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-base outline-none ring-green-100 focus:border-green-600 focus:ring-2 sm:text-sm"
        placeholder={placeholder}
      />
      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={onBack}
          disabled={isAnalyzing}
          className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
        >
          Назад
        </button>
        <button
          type="button"
          onClick={onAnalyze}
          disabled={!value.trim() || isAnalyzing}
          className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isAnalyzing ? "Анализирую…" : "Анализировать"}
        </button>
      </div>
    </div>
  );
}

export function AddMealModal({ open, onClose, onMealSaved, mealLocalDate }: AddMealModalProps) {
  const { validateSession, getAccessToken } = useAuth();
  const [ui, setUi] = useState<UiState>({ kind: "menu" });
  const [takeAdditiveOpen, setTakeAdditiveOpen] = useState(false);
  const [waterSaving, setWaterSaving] = useState(false);
  const [textDraft, setTextDraft] = useState("");
  const [textDescription, setTextDescription] = useState("");
  const [photoComment, setPhotoComment] = useState("");
  const [selectedImageBase64, setSelectedImageBase64] = useState<string | null>(null);
  const [correctionHistory, setCorrectionHistory] = useState<string[]>([]);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [scheduled, setScheduled] = useState<ScheduledLocal | null>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const photoB64Ref = useRef<string | null>(null);

  const reset = useCallback(() => {
    setUi({ kind: "menu" });
    setTextDraft("");
    setTextDescription("");
    setPhotoComment("");
    setSelectedImageBase64(null);
    setCorrectionHistory([]);
    setInlineError(null);
    photoB64Ref.current = null;
  }, []);

  const updateConfirmMealData = useCallback((updater: (mealData: MealData) => MealData) => {
    setUi((prev) => {
      if (prev.kind !== "confirm") return prev;
      return { kind: "confirm", mealData: updater(prev.mealData) };
    });
  }, []);

  const tomorrowYmd = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return formatLocalYmd(d);
  }, []);

  useEffect(() => {
    if (open) {
      reset();
      setTakeAdditiveOpen(false);
      setWaterSaving(false);
      if (mealLocalDate) {
        setScheduled(buildDefaultScheduled(mealLocalDate));
      } else {
        setScheduled(null);
      }
    }
  }, [open, reset, mealLocalDate]);

  const scheduleBlock =
    scheduled != null ? (
      <MealScheduledTimeBlock
        scheduled={scheduled}
        tomorrowYmd={tomorrowYmd}
        onScheduledChange={setScheduled}
      />
    ) : null;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const runAnalyzeImage = async () => {
    if (!selectedImageBase64) return;
    setInlineError(null);
    setUi({ kind: "busy", message: "Анализирую фото…" });
    try {
      const sessionOk = await validateSession();
      const token = getAccessToken();
      if (!sessionOk || !token) {
        setUi({ kind: "error", message: "Сессия истекла. Войдите снова." });
        return;
      }
      photoB64Ref.current = selectedImageBase64;
      const raw = await analyzeMealImageBase64(token, selectedImageBase64, {
        comment: photoComment.trim() || null,
      });
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "photo_preview" });
        setInlineError(parsed.error || "Не удалось разобрать еду на фото. Попробуйте ещё раз или добавьте комментарий.");
        return;
      }
      const { ingredients, confidence, nutrition, prediction, prediction_translated, prediction_language } =
        parsed;
      setUi({
        kind: "recognition",
        mealData: {
          ingredients,
          confidence,
          nutrition,
          source_type: "photo",
          telegram_file_id: null,
          prediction,
          prediction_translated,
          prediction_language,
          user_text: photoComment.trim() || null,
          image_base64: selectedImageBase64,
        },
      });
    } catch (err) {
      setUi({ kind: "photo_preview" });
      const message = axios.isAxiosError(err) ? String(err.response?.data?.detail ?? err.message) : "Ошибка сети.";
      setInlineError(message);
    }
  };

  const runAnalyzePhotoCorrection = async (previousMealData: MealData, correction: string) => {
    const trimmed = correction.trim();
    if (!selectedImageBase64 || !trimmed) return;
    const nextHistory = [...correctionHistory, trimmed];
    setInlineError(null);
    setUi({ kind: "busy", message: "Учитываю коррекцию…" });
    try {
      const sessionOk = await validateSession();
      const token = getAccessToken();
      if (!sessionOk || !token) {
        setUi({ kind: "error", message: "Сессия истекла. Войдите снова." });
        return;
      }
      const raw = await analyzeMealImageWithText(
        token,
        selectedImageBase64,
        trimmed,
        previousMealData.ingredients,
        previousMealData.prediction,
        photoComment.trim() || null,
        nextHistory,
      );
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({
          kind: "text",
          mode: "after_photo",
          hint: parsed.error || "Не удалось учесть коррекцию. Попробуйте сформулировать иначе.",
          previousMealData,
        });
        return;
      }
      const { ingredients, confidence, nutrition, prediction, prediction_translated, prediction_language } =
        parsed;
      setCorrectionHistory(nextHistory);
      setTextDraft("");
      setUi({
        kind: "recognition",
        mealData: {
          ingredients,
          confidence,
          nutrition,
          source_type: "photo",
          telegram_file_id: null,
          prediction,
          prediction_translated,
          prediction_language,
          user_text: [photoComment.trim(), ...nextHistory].filter(Boolean).join("\n"),
          image_base64: selectedImageBase64,
        },
      });
    } catch (err) {
      setUi({
        kind: "text",
        mode: "after_photo",
        hint: axios.isAxiosError(err)
          ? String(err.response?.data?.detail ?? err.message)
          : "Не удалось учесть коррекцию. Попробуйте ещё раз.",
        previousMealData,
      });
    }
  };

  const runAnalyzeText = async (text: string, mode: "standalone" | "after_photo") => {
    const trimmed = text.trim();
    const previousMealData = ui.kind === "text" ? ui.previousMealData : null;
    setInlineError(null);
    if (!trimmed) {
      setUi({ kind: "error", message: "Введите описание блюда." });
      return;
    }
    setUi({
      kind: "busy",
      message: mode === "after_photo" ? "Анализирую фото и описание…" : "Анализирую описание…",
    });
    try {
      const sessionOk = await validateSession();
      const token = getAccessToken();
      if (!sessionOk || !token) {
        setUi({ kind: "error", message: "Сессия истекла. Войдите снова." });
        return;
      }
      const raw =
        mode === "after_photo" && photoB64Ref.current
          ? await analyzeMealImageWithText(
              token,
              photoB64Ref.current,
              trimmed,
              previousMealData?.ingredients ?? null,
              previousMealData?.prediction ?? null,
              photoComment.trim() || null,
              previousMealData ? [...correctionHistory, trimmed] : correctionHistory,
            )
          : await analyzeMealText(
              token,
              previousMealData ? textDescription : trimmed,
              previousMealData
                ? {
                    previous_ingredients: previousMealData.ingredients,
                    previous_prediction: previousMealData.prediction,
                    correction: trimmed,
                    correction_history: [...correctionHistory, trimmed],
                  }
                : {},
            );
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({
          kind: "text",
          mode,
          hint: parsed.error || "Ошибка анализа текста.",
          previousMealData,
        });
        return;
      }
      const { ingredients, confidence, nutrition, prediction, prediction_translated, prediction_language } =
        parsed;
      if (!previousMealData && mode === "standalone") {
        setTextDescription(trimmed);
      }
      if (previousMealData) {
        setCorrectionHistory((history) => [...history, trimmed]);
      }
      const mealData: MealData = {
        ingredients,
        confidence,
        nutrition,
        source_type: mode === "after_photo" ? "photo_text" : "text",
        telegram_file_id: null,
        prediction,
        prediction_translated,
        prediction_language,
        user_text: trimmed,
        ...(mode === "after_photo" && photoB64Ref.current
          ? { image_base64: photoB64Ref.current }
          : {}),
      };
      setTextDraft("");
      setUi({ kind: "recognition", mealData });
    } catch (err) {
      setUi({
        kind: "text",
        mode,
        hint: axios.isAxiosError(err) ? String(err.response?.data?.detail ?? err.message) : "Ошибка сети.",
        previousMealData,
      });
    }
  };

  const onImageSelected = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    void (async () => {
      try {
        const b64 = await fileToBase64(f);
        setSelectedImageBase64(b64);
        photoB64Ref.current = b64;
        setPhotoComment("");
        setTextDraft("");
        setCorrectionHistory([]);
        setUi({ kind: "photo_preview" });
      } catch {
        setUi({ kind: "error", message: "Не удалось прочитать файл." });
      }
    })();
  };

  const confirmSave = async () => {
    if (ui.kind !== "confirm") return;
    if (scheduled) {
      const err = validateScheduled(scheduled, tomorrowYmd);
      if (err) {
        setUi({ kind: "error", message: err });
        return;
      }
    }
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
        prediction_translated: ui.mealData.prediction_translated ?? null,
        prediction_language: ui.mealData.prediction_language ?? null,
        user_text: ui.mealData.user_text ?? undefined,
        image_base64: ui.mealData.image_base64 ?? undefined,
        meal_local_datetime: scheduled ? toMealLocalDatetime(scheduled) : undefined,
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

  const token = getAccessToken();

  return (
    <>
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
              {scheduleBlock}
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
                  setTextDescription("");
                  setCorrectionHistory([]);
                  setInlineError(null);
                  photoB64Ref.current = null;
                  setUi({ kind: "text", mode: "standalone" });
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-100"
              >
                <PenLine className="h-5 w-5 shrink-0" aria-hidden />
                Написать текстом
              </button>
              <button
                type="button"
                onClick={() => setTakeAdditiveOpen(true)}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
              >
                <Pill className="h-5 w-5 shrink-0" aria-hidden />
                Принять добавку
              </button>
              <WaterButton
                saving={waterSaving}
                className="w-full"
                onRecord={(amountMl) => void (async () => {
                  const sessionOk = await validateSession();
                  const token = getAccessToken();
                  if (!sessionOk || !token) {
                    setUi({ kind: "error", message: "Сессия истекла. Войдите снова." });
                    return;
                  }
                  setWaterSaving(true);
                  try {
                    const now = new Date();
                    const timeLocal = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
                    await recordWaterIntake(token, {
                      amount_ml: amountMl,
                      intake_local_date: mealLocalDate ?? undefined,
                      intake_local_time: timeLocal,
                    });
                    onMealSaved?.();
                    onClose();
                  } catch (err) {
                    setUi({
                      kind: "error",
                      message: err instanceof Error ? err.message : "Не удалось записать воду.",
                    });
                  } finally {
                    setWaterSaving(false);
                  }
                })()}
              />
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

          {ui.kind === "photo_preview" ? (
            <div className="space-y-4">
              {scheduleBlock}
              <MealPhotoPreview imageBase64={selectedImageBase64} />
              {inlineError ? (
                <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-800">{inlineError}</p>
              ) : null}
              <label className="block text-sm font-medium text-slate-700">Комментарий</label>
              <textarea
                value={photoComment}
                onChange={(e) => setPhotoComment(e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-base outline-none ring-green-100 focus:border-green-600 focus:ring-2 sm:text-sm"
                placeholder="Например: это цикорий, не кофе; салат с йогуртовой заправкой; мясо без масла"
              />
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={reset}
                  className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Назад
                </button>
                <button
                  type="button"
                  onClick={() => void runAnalyzeImage()}
                  disabled={!selectedImageBase64}
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Анализировать
                </button>
              </div>
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
              {scheduleBlock}
              <MealPredictionConfirmStep
                mealData={ui.mealData}
                onConfirm={() => setUi({ kind: "confirm", mealData: ui.mealData })}
                onCorrection={() => {
                  setTextDraft("");
                  setInlineError(null);
                  setUi({
                    kind: "text",
                    mode: ui.mealData.image_base64 ? "after_photo" : "standalone",
                    hint: ui.mealData.image_base64 ? undefined : "Опиши, что нужно исправить в составе блюда.",
                    previousMealData: ui.mealData,
                  });
                }}
              />
            </div>
          ) : null}

          {ui.kind === "text" ? (
            <div className="space-y-3">
              {scheduleBlock}
              {ui.hint ? <p className="text-sm text-slate-600">{ui.hint}</p> : null}
              {inlineError ? (
                <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-800">{inlineError}</p>
              ) : null}
              {ui.previousMealData ? (
                <MealCorrectionStep
                  imageBase64={ui.previousMealData.image_base64}
                  value={textDraft}
                  onChange={setTextDraft}
                  isAnalyzing={false}
                  placeholder={
                    ui.mode === "after_photo"
                      ? "Что исправить в распознавании фото?\nНапример: это цикорий, не кофе; заправка йогуртовая, не майонез"
                      : undefined
                  }
                  onBack={() => {
                    setInlineError(null);
                    setTextDraft("");
                    setUi({ kind: "recognition", mealData: ui.previousMealData as MealData });
                  }}
                  onAnalyze={() =>
                    ui.mode === "after_photo" && ui.previousMealData
                      ? void runAnalyzePhotoCorrection(ui.previousMealData, textDraft)
                      : void runAnalyzeText(textDraft, ui.mode)
                  }
                />
              ) : (
                <>
                  <label className="block text-sm font-medium text-slate-700">Описание блюда</label>
                  <textarea
                    value={textDraft}
                    onChange={(e) => setTextDraft(e.target.value)}
                    rows={5}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-base outline-none ring-green-100 focus:border-green-600 focus:ring-2 sm:text-sm"
                    placeholder="Например: гречка с курицей 300 г, салат из огурцов 150 г"
                  />
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      onClick={() => void runAnalyzeText(textDraft, ui.mode)}
                      disabled={!textDraft.trim()}
                      className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
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
                </>
              )}
            </div>
          ) : null}

          {ui.kind === "confirm" ? (
            <div className="space-y-4">
              {scheduleBlock}
            <MealCompositionForm
              mealData={{
                ingredients: ui.mealData.ingredients,
                nutrition: ui.mealData.nutrition,
                prediction: ui.mealData.prediction,
                prediction_translated: ui.mealData.prediction_translated,
                prediction_language: ui.mealData.prediction_language,
                image_base64: ui.mealData.image_base64,
              }}
              accessToken={getAccessToken() ?? undefined}
              onMealDataChange={(comp: MealCompositionState) =>
                updateConfirmMealData((md) => ({
                  ...md,
                  ingredients: comp.ingredients,
                  nutrition: comp.nutrition,
                  prediction: comp.prediction,
                  prediction_translated: comp.prediction_translated,
                  prediction_language: comp.prediction_language,
                }))
              }
              savePrompt="Записать прием пищи в дневник?"
              primaryLabel="Да, записать"
              secondaryLabel="Отмена"
              onPrimary={() => void confirmSave()}
              onSecondary={() => {
                reset();
                onClose();
              }}
            />
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

    {token ? (
      <TakeAdditiveModal
        open={takeAdditiveOpen}
        accessToken={token}
        dateYmd={mealLocalDate ?? null}
        onClose={() => setTakeAdditiveOpen(false)}
        onSaved={() => {
          onMealSaved?.();
          onClose();
        }}
      />
    ) : null}
    </>
  );
}
