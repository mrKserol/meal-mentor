import { type ChangeEvent, useCallback, useEffect, useRef, useState } from "react";
import { Camera, Loader2, X } from "lucide-react";

import { analyzeAdditiveImageBase64, createAdditive, getAdditiveNutrientFields } from "../../api/additivesApi";
import type { NutrientField } from "../../types/additives";
import { fileToBase64 } from "../../utils/mealFlow";
import { AdditiveNutrientsForm } from "./AdditiveNutrientsForm";

type Props = {
  open: boolean;
  accessToken: string;
  onClose: () => void;
  onSaved: () => void;
};

export function CreateAdditiveModal({ open, accessToken, onClose, onSaved }: Props) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<"intro" | "analyzing" | "form" | "saving" | "error">("intro");
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [additiveName, setAdditiveName] = useState("");
  const [servingLabel, setServingLabel] = useState("");
  const [servingSizeG, setServingSizeG] = useState("");
  const [nutrients, setNutrients] = useState<Record<string, number>>({});
  const [ignored, setIgnored] = useState<Array<{ label: string; amount: string | null; reason?: string }>>([]);
  const [nutrientFields, setNutrientFields] = useState<NutrientField[]>([]);

  const reset = useCallback(() => {
    setPhase("intro");
    setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setImageB64(null);
    setAdditiveName("");
    setServingLabel("");
    setServingSizeG("");
    setNutrients({});
    setIgnored([]);
  }, [previewUrl]);

  useEffect(() => {
    if (!open) return;
    reset();
    void getAdditiveNutrientFields(accessToken)
      .then(setNutrientFields)
      .catch(() => setNutrientFields([]));
  }, [open, accessToken, reset]);

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setPhase("analyzing");
    setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    try {
      const b64 = await fileToBase64(file);
      setImageB64(b64);
      const res = await analyzeAdditiveImageBase64(accessToken, b64);
      if (res.status !== "success") {
        setPhase("error");
        setError(res.error || "Не удалось распознать этикетку.");
        return;
      }
      setServingLabel(res.serving_label ?? "");
      setServingSizeG(res.serving_size_g != null ? String(res.serving_size_g) : "");
      setNutrients(res.nutrients ?? {});
      setIgnored(res.ignored ?? []);
      setPhase("form");
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : "Ошибка анализа");
    }
  };

  const handleSave = async () => {
    const name = additiveName.trim();
    if (!name) {
      setError("Укажите название добавки.");
      return;
    }
    setPhase("saving");
    setError(null);
    try {
      const cleanNutrients: Record<string, number> = {};
      for (const [k, v] of Object.entries(nutrients)) {
        if (v != null && !Number.isNaN(v) && v > 0) cleanNutrients[k] = v;
      }
      const sizeG = servingSizeG.trim() ? parseFloat(servingSizeG.replace(",", ".")) : null;
      await createAdditive(accessToken, {
        additive_name: name,
        serving_label: servingLabel.trim() || null,
        serving_size_g: sizeG != null && !Number.isNaN(sizeG) ? sizeG : null,
        image_base64: imageB64,
        nutrients: cleanNutrients,
      });
      onSaved();
      onClose();
    } catch (err) {
      setPhase("form");
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
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
        className="flex max-h-[min(92vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-900">Создать добавку</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100">
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {phase === "intro" ? (
            <>
              <p className="text-sm text-slate-600 text-center">
                Сфотографируйте состав одной порции добавки на обратной стороне упаковки
              </p>
              <button
                type="button"
                onClick={() => cameraRef.current?.click()}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white"
              >
                <Camera className="h-5 w-5" aria-hidden />
                Сфотографировать
              </button>
              <input
                ref={cameraRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="sr-only"
                onChange={onFile}
              />
            </>
          ) : null}

          {phase === "analyzing" ? (
            <div className="flex flex-col items-center gap-3 py-8 text-slate-600">
              <Loader2 className="h-10 w-10 animate-spin text-green-600" aria-hidden />
              <p className="text-sm">Распознаём этикетку…</p>
            </div>
          ) : null}

          {phase === "form" || phase === "saving" ? (
            <>
              {previewUrl ? (
                <img src={previewUrl} alt="" className="mx-auto max-h-40 rounded-xl object-contain" />
              ) : null}
              <label className="block text-sm font-medium text-slate-700">
                Название добавки
                <input
                  value={additiveName}
                  onChange={(e) => setAdditiveName(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Порция (подпись)
                <input
                  value={servingLabel}
                  onChange={(e) => setServingLabel(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Вес порции, г
                <input
                  type="number"
                  step="any"
                  value={servingSizeG}
                  onChange={(e) => setServingSizeG(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <AdditiveNutrientsForm
                nutrients={nutrients}
                nutrientFields={nutrientFields}
                onChange={setNutrients}
              />
              {ignored.length > 0 ? (
                <div className="rounded-xl bg-slate-100 px-3 py-2 text-xs text-slate-600 space-y-1">
                  <p className="font-medium">Не учтено на этикетке:</p>
                  {ignored.map((item, i) => (
                    <p key={`${item.label}-${i}`}>
                      {item.label}
                      {item.amount ? ` — ${item.amount}` : ""}
                    </p>
                  ))}
                </div>
              ) : null}
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={phase === "saving"}
                  onClick={() => void handleSave()}
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white disabled:opacity-50"
                >
                  Сохранить
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-700"
                >
                  Отмена
                </button>
              </div>
            </>
          ) : null}

          {phase === "error" && error ? (
            <div className="space-y-3">
              <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
              <button
                type="button"
                onClick={() => setPhase("intro")}
                className="w-full rounded-xl bg-slate-100 py-2 text-sm font-semibold text-slate-800"
              >
                Попробовать снова
              </button>
            </div>
          ) : null}
          {error && phase === "form" ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
