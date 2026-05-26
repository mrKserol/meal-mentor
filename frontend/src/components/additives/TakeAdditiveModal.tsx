import { useCallback, useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";

import { listAdditives, recordAdditiveIntake } from "../../api/additivesApi";
import type { AdditiveItem } from "../../types/additives";

type Props = {
  open: boolean;
  accessToken: string;
  dateYmd: string | null;
  onClose: () => void;
  onSaved: () => void;
};

export function TakeAdditiveModal({ open, accessToken, dateYmd, onClose, onSaved }: Props) {
  const [items, setItems] = useState<AdditiveItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [servings, setServings] = useState("1");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAdditives(accessToken);
      setItems(res.items);
      if (res.items.length > 0 && selectedId == null) {
        setSelectedId(res.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить добавки");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (!open) return;
    setServings("1");
    setSelectedId(null);
    setError(null);
    void load();
  }, [open, load]);

  const servingsNum = parseFloat(servings.replace(",", "."));
  const canSubmit = selectedId != null && servingsNum > 0 && !Number.isNaN(servingsNum);

  const handleSubmit = async () => {
    if (!canSubmit || selectedId == null) return;
    setSaving(true);
    setError(null);
    try {
      const now = new Date();
      const timeLocal = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
      await recordAdditiveIntake(accessToken, {
        additive_id: selectedId,
        servings_count: servingsNum,
        intake_local_date: dateYmd ?? undefined,
        intake_local_time: timeLocal,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось записать приём");
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

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
        className="flex max-h-[min(85vh,560px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-900">Принять добавку</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100">
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>
        <div className="px-4 py-4 space-y-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-green-600" aria-hidden />
            </div>
          ) : items.length === 0 ? (
            <p className="text-sm text-slate-600 text-center py-4">
              У вас пока нет добавок. Создайте добавку в профиле.
            </p>
          ) : (
            <>
              <label className="block text-sm font-medium text-slate-700">
                Добавка
                <select
                  value={selectedId ?? ""}
                  onChange={(e) => setSelectedId(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                >
                  {items.map((it) => (
                    <option key={it.id} value={it.id}>
                      {it.additive_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Количество порций
                <input
                  type="number"
                  min={0.01}
                  step="any"
                  value={servings}
                  onChange={(e) => setServings(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
            </>
          )}
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!canSubmit || saving || items.length === 0}
              onClick={() => void handleSubmit()}
              className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? <Loader2 className="mx-auto h-5 w-5 animate-spin" aria-hidden /> : "Принять"}
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
