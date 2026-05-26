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
  needsUserDescription,
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

function formatScheduledHint(dateYmd: string, timeHm: string): string {
  const [y, mo, da] = dateYmd.split("-").map(Number);
  const [hh, mm] = timeHm.split(":").map(Number);
  const dt = new Date(y, mo - 1, da, hh, mm);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(dt);
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
  editOpen,
  onEditOpenChange,
  onScheduledChange,
}: {
  scheduled: ScheduledLocal;
  tomorrowYmd: string;
  editOpen: boolean;
  onEditOpenChange: (open: boolean) => void;
  onScheduledChange: (next: ScheduledLocal) => void;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!editOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      const root = wrapRef.current;
      if (!root || root.contains(e.target as Node)) return;
      onEditOpenChange(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [editOpen, onEditOpenChange]);

  return (
    <div ref={wrapRef} className="space-y-2">
      <button
        type="button"
        onClick={() => onEditOpenChange(!editOpen)}
        className="w-full rounded-xl border border-green-200 bg-green-50 px-3 py-2.5 text-center text-sm text-green-900 transition hover:bg-green-100"
      >
        Приём будет записан на {formatScheduledHint(scheduled.date, scheduled.time)}
      </button>
      {editOpen ? (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_7.5rem] sm:items-end sm:gap-2">
            <label className="block min-w-0 max-w-full text-sm">
              <span className="mb-1 block font-medium text-slate-700">Дата</span>
              <input
                type="date"
                value={scheduled.date}
                max={tomorrowYmd}
                onChange={(e) => {
                  const v = e.target.value;
                  if (!v) return;
                  onScheduledChange({ ...scheduled, date: v > tomorrowYmd ? tomorrowYmd : v });
                }}
                className="box-border w-full min-w-0 max-w-full rounded-lg border border-slate-200 px-3 py-2"
              />
            </label>
            <label className="block min-w-0 w-full max-w-full text-sm sm:w-auto sm:max-w-[7.5rem]">
              <span className="mb-1 block font-medium text-slate-700">Время</span>
              <div className="min-w-0 w-full max-w-full overflow-hidden">
                <input
                  type="time"
                  value={scheduled.time}
                  onChange={(e) => onScheduledChange({ ...scheduled, time: e.target.value })}
                  className="meal-time-input box-border w-full min-w-0 max-w-full rounded-lg border border-slate-200 px-2 py-2 text-sm sm:px-2.5"
                />
              </div>
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function AddMealModal({ open, onClose, onMealSaved, mealLocalDate }: AddMealModalProps) {
  const { validateSession, getAccessToken } = useAuth();
  const [ui, setUi] = useState<UiState>({ kind: "menu" });
  const [takeAdditiveOpen, setTakeAdditiveOpen] = useState(false);
  const [waterSaving, setWaterSaving] = useState(false);
  const [textDraft, setTextDraft] = useState("");
  const [scheduled, setScheduled] = useState<ScheduledLocal | null>(null);
  const [scheduleEditOpen, setScheduleEditOpen] = useState(false);
  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const photoB64Ref = useRef<string | null>(null);

  const reset = useCallback(() => {
    setUi({ kind: "menu" });
    setTextDraft("");
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
      setScheduleEditOpen(false);
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
        editOpen={scheduleEditOpen}
        onEditOpenChange={setScheduleEditOpen}
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

  const runAnalyzeImage = async (file: File) => {
    setUi({ kind: "busy", message: "Анализирую фото…" });
    try {
      const sessionOk = await validateSession();
      const token = getAccessToken();
      if (!sessionOk || !token) {
        setUi({ kind: "error", message: "Сессия истекла. Войдите снова." });
        return;
      }
      const b64 = await fileToBase64(file);
      photoB64Ref.current = b64;
      const raw = await analyzeMealImageBase64(token, b64);
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "error", message: parsed.error || "Не удалось разобрать еду на фото." });
        return;
      }
      const { ingredients, confidence, nutrition, prediction, prediction_translated, prediction_language } =
        parsed;
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
          prediction_translated,
          prediction_language,
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
    const previousMealData = ui.kind === "text" ? ui.previousMealData : null;
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
            )
          : await analyzeMealText(token, trimmed);
      const parsed = parseAnalyzeResponse(raw);
      if (parsed.status !== "success") {
        setUi({ kind: "error", message: parsed.error || "Ошибка анализа текста." });
        return;
      }
      const { ingredients, confidence, nutrition, prediction, prediction_translated, prediction_language } =
        parsed;
      if (needsUserDescription(ingredients, confidence)) {
        setUi({
          kind: "text",
          mode,
          hint:
            mode === "after_photo"
              ? "Не получилось выделить еду. Уточни подробнее: что на фото и примерные порции."
              : "По описанию мало данных. Добавь деталей: что именно и сколько примерно по весу.",
          previousMealData,
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
        prediction_translated,
        prediction_language,
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
    if (scheduled) {
      const err = validateScheduled(scheduled, tomorrowYmd);
      if (err) {
        setUi({ kind: "error", message: err });
        setScheduleEditOpen(true);
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

          {ui.kind === "busy" ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-slate-600">
              <Loader2 className="h-10 w-10 animate-spin text-green-600" aria-hidden />
              <p className="text-sm font-medium">{ui.message}</p>
            </div>
          ) : null}

          {ui.kind === "recognition" ? (
            <div className="space-y-4">
              {scheduleBlock}
              <MealPhotoPreview imageBase64={ui.mealData.image_base64} />
              <div className="space-y-3 text-center text-sm leading-relaxed text-slate-800">
                {mealDisplayPrediction(ui.mealData) ? (
                  <p>
                    Похоже, что это:{" "}
                    <span className="text-[15px] font-bold leading-snug text-slate-900">
                      {mealDisplayPrediction(ui.mealData)}
                    </span>
                  </p>
                ) : null}
                <p className="font-medium text-slate-900">Примерный состав:</p>
                <p>
                  {Object.keys(ui.mealData.ingredients).length
                    ? Object.entries(ui.mealData.ingredients)
                        .map(([name, entry]) => ingredientDisplayName(name, entry))
                        .join(" • ")
                    : "—"}
                </p>
                <p>Я верно определил?</p>
              </div>
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
                    setUi({
                      kind: "text",
                      mode: "after_photo",
                      hint: "Опиши блюдо на фото и примерные порции.",
                      previousMealData: ui.mealData,
                    });
                  }}
                  className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
                >
                  Нет, коррекция
                </button>
              </div>
            </div>
          ) : null}

          {ui.kind === "text" ? (
            <div className="space-y-3">
              {scheduleBlock}
              {ui.mode === "after_photo" ? (
                <MealPhotoPreview imageBase64={photoB64Ref.current} />
              ) : null}
              {ui.hint ? <p className="text-sm text-slate-600">{ui.hint}</p> : null}
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
