import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";

import { getAdditiveNutrientFields, updateAdditive } from "../../api/additivesApi";
import type { AdditiveItem, NutrientField } from "../../types/additives";
import { AdditiveNutrientsForm } from "./AdditiveNutrientsForm";

type Props = {
  open: boolean;
  accessToken: string;
  additive: AdditiveItem | null;
  onClose: () => void;
  onSaved: () => void;
};

export function EditAdditiveModal({ open, accessToken, additive, onClose, onSaved }: Props) {
  const [additiveName, setAdditiveName] = useState("");
  const [servingLabel, setServingLabel] = useState("");
  const [servingSizeG, setServingSizeG] = useState("");
  const [nutrients, setNutrients] = useState<Record<string, number>>({});
  const [nutrientFields, setNutrientFields] = useState<NutrientField[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !additive) return;
    setAdditiveName(additive.additive_name);
    setServingLabel(additive.serving_label ?? "");
    setServingSizeG(additive.serving_size_g != null ? String(additive.serving_size_g) : "");
    setNutrients({ ...additive.nutrients });
    setError(null);
    void getAdditiveNutrientFields(accessToken)
      .then(setNutrientFields)
      .catch(() => setNutrientFields([]));
  }, [open, additive, accessToken]);

  const handleSave = async () => {
    if (!additive) return;
    const name = additiveName.trim();
    if (!name) {
      setError("Укажите название.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const cleanNutrients: Record<string, number> = {};
      for (const [k, v] of Object.entries(nutrients)) {
        if (v != null && !Number.isNaN(v) && v > 0) cleanNutrients[k] = v;
      }
      const sizeG = servingSizeG.trim() ? parseFloat(servingSizeG.replace(",", ".")) : null;
      await updateAdditive(accessToken, additive.id, {
        additive_name: name,
        serving_label: servingLabel.trim() || null,
        serving_size_g: sizeG != null && !Number.isNaN(sizeG) ? sizeG : null,
        nutrients: cleanNutrients,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  };

  if (!open || !additive) return null;

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
        className="flex max-h-[min(92vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-900">Редактировать добавку</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100">
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 space-y-4">
          <label className="block text-sm font-medium text-slate-700">
            Название
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
          <AdditiveNutrientsForm nutrients={nutrients} nutrientFields={nutrientFields} onChange={setNutrients} />
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={saving}
              onClick={() => void handleSave()}
              className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? <Loader2 className="mx-auto h-5 w-5 animate-spin" aria-hidden /> : "Да, сохранить"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 py-3 text-sm font-semibold text-slate-700"
            >
              Отмена
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
