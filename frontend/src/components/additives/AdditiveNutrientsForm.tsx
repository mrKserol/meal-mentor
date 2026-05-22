import { useMemo, useState } from "react";
import { Minus, Plus } from "lucide-react";

import type { NutrientField } from "../../types/additives";

type Props = {
  nutrients: Record<string, number>;
  nutrientFields: NutrientField[];
  onChange: (nutrients: Record<string, number>) => void;
};

export function AdditiveNutrientsForm({ nutrients, nutrientFields, onChange }: Props) {
  const [addOpen, setAddOpen] = useState(false);
  const [pickKey, setPickKey] = useState("");
  const [pickAmount, setPickAmount] = useState("");

  const keys = useMemo(() => Object.keys(nutrients).filter((k) => nutrients[k] != null && !Number.isNaN(nutrients[k])), [
    nutrients,
  ]);

  const availableToAdd = useMemo(
    () => nutrientFields.filter((f) => !keys.includes(f.key)),
    [nutrientFields, keys],
  );

  const fieldByKey = useMemo(() => {
    const m = new Map<string, NutrientField>();
    for (const f of nutrientFields) m.set(f.key, f);
    return m;
  }, [nutrientFields]);

  const updateAmount = (key: string, raw: string) => {
    const n = parseFloat(raw.replace(",", "."));
    if (raw === "" || Number.isNaN(n)) {
      const next = { ...nutrients };
      delete next[key];
      onChange(next);
      return;
    }
    onChange({ ...nutrients, [key]: n });
  };

  const removeKey = (key: string) => {
    const next = { ...nutrients };
    delete next[key];
    onChange(next);
  };

  const handleAdd = () => {
    if (!pickKey) return;
    const n = parseFloat(pickAmount.replace(",", "."));
    if (!pickKey || Number.isNaN(n) || n <= 0) return;
    onChange({ ...nutrients, [pickKey]: n });
    setPickKey("");
    setPickAmount("");
    setAddOpen(false);
  };

  return (
    <div className="space-y-3">
      {keys.length === 0 ? (
        <p className="text-sm text-slate-500">Нутриенты не указаны.</p>
      ) : (
        <ul className="space-y-2">
          {keys.map((key) => {
            const field = fieldByKey.get(key);
            const label = field?.label ?? key;
            const unit = field?.unit ?? "";
            return (
              <li key={key} className="flex items-center gap-2">
                <span className="min-w-0 flex-1 text-sm font-medium text-slate-700">{label}</span>
                <input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  value={nutrients[key]}
                  onChange={(e) => updateAmount(key, e.target.value)}
                  className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                />
                {unit ? <span className="w-10 text-xs text-slate-500">{unit}</span> : null}
                <button
                  type="button"
                  onClick={() => removeKey(key)}
                  className="rounded-lg p-1.5 text-red-600 transition hover:bg-red-50"
                  aria-label={`Удалить ${label}`}
                >
                  <Minus className="h-4 w-4" aria-hidden />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <button
        type="button"
        onClick={() => setAddOpen((v) => !v)}
        className="flex items-center gap-1 text-sm font-semibold text-green-700 transition hover:text-green-800"
      >
        <Plus className="h-4 w-4" aria-hidden />
        Добавить нутриент
      </button>

      {addOpen ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-2">
          <select
            value={pickKey}
            onChange={(e) => setPickKey(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="">Выберите нутриент</option>
            {availableToAdd.map((f) => (
              <option key={f.key} value={f.key}>
                {f.label} ({f.unit})
              </option>
            ))}
          </select>
          <input
            type="number"
            step="any"
            inputMode="decimal"
            placeholder="Количество"
            value={pickAmount}
            onChange={(e) => setPickAmount(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!pickKey || !pickAmount}
            className="w-full rounded-lg bg-green-600 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Добавить
          </button>
        </div>
      ) : null}
    </div>
  );
}
