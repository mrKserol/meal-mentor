import { useCallback, useEffect, useState } from "react";
import { Droplets, Loader2, Pill, X } from "lucide-react";

import {
  deleteAdditiveIntake,
  getAdditiveIntakesForDay,
  recordWaterIntake,
} from "../../api/additivesApi";
import type { AdditiveIntakeItem } from "../../types/additives";
import { SwipeDeleteRow } from "../common/SwipeDeleteRow";
import { TakeAdditiveModal } from "./TakeAdditiveModal";

type Props = {
  open: boolean;
  dateYmd: string;
  accessToken: string;
  onClose: () => void;
  onChanged: () => void;
};

function ymdToRuShort(ymd: string): string {
  const [y, mo, da] = ymd.split("-").map(Number);
  const dt = new Date(y, mo - 1, da);
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(dt);
}

function intakeSummary(item: AdditiveIntakeItem): string | null {
  const parts: string[] = [];
  const n = item.nutrients;
  if (n.calories) parts.push(`${Math.round(n.calories)} kcal`);
  if (n.protein_g) parts.push(`Б ${Math.round(n.protein_g)} г`);
  if (n.fat_g) parts.push(`Ж ${Math.round(n.fat_g)} г`);
  if (n.carbs_g) parts.push(`У ${Math.round(n.carbs_g)} г`);
  return parts.length ? parts.join(" · ") : null;
}

export function AdditiveIntakesDayModal({ open, dateYmd, accessToken, onClose, onChanged }: Props) {
  const [items, setItems] = useState<AdditiveIntakeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [takeOpen, setTakeOpen] = useState(false);
  const [waterSaving, setWaterSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAdditiveIntakesForDay(accessToken, dateYmd);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }, [accessToken, dateYmd]);

  useEffect(() => {
    if (open) void load();
  }, [open, load]);

  const handleDelete = async (id: number) => {
    if (deletingId != null) return;
    setDeletingId(id);
    try {
      await deleteAdditiveIntake(accessToken, id);
      await load();
      onChanged();
    } finally {
      setDeletingId(null);
    }
  };

  const handleWater = async () => {
    setWaterSaving(true);
    try {
      await recordWaterIntake(accessToken, { amount_ml: 100, intake_local_date: dateYmd });
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось записать воду");
    } finally {
      setWaterSaving(false);
    }
  };

  if (!open) return null;

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
          className="flex max-h-[min(88vh,680px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Добавки за день</h2>
              <p className="text-xs text-slate-500 capitalize">{ymdToRuShort(dateYmd)}</p>
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100">
              <X className="h-5 w-5" aria-hidden />
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-8 w-8 animate-spin text-green-600" aria-hidden />
              </div>
            ) : null}
            {error ? <p className="px-4 py-2 text-sm text-red-600">{error}</p> : null}
            {!loading && items.length === 0 ? (
              <p className="p-8 text-center text-sm text-slate-500">За этот день добавки не отмечены.</p>
            ) : null}
            {items.map((item) => (
              <SwipeDeleteRow
                key={item.id}
                disabled={deletingId === item.id}
                onDelete={() => void handleDelete(item.id)}
              >
                <div className="px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-slate-900">{item.additive_name_snapshot}</p>
                    <span className="text-sm text-slate-500 shrink-0">{item.time_local}</span>
                  </div>
                  {item.water_g != null && item.water_g > 0 ? (
                    <p className="mt-1 text-sm text-sky-700">Вода: {Math.round(item.water_g)} мл</p>
                  ) : (
                    <p className="mt-1 text-xs text-slate-500">Порций: {item.servings_count}</p>
                  )}
                  {intakeSummary(item) ? (
                    <p className="mt-1 text-xs text-slate-600">{intakeSummary(item)}</p>
                  ) : null}
                </div>
              </SwipeDeleteRow>
            ))}
          </div>

          <div className="border-t border-slate-100 p-4 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={() => setTakeOpen(true)}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-green-600 py-2.5 text-sm font-semibold text-white"
            >
              <Pill className="h-4 w-4" aria-hidden />
              Принять добавку
            </button>
            <button
              type="button"
              disabled={waterSaving}
              onClick={() => void handleWater()}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-sky-200 bg-sky-50 py-2.5 text-sm font-semibold text-sky-800 disabled:opacity-50"
            >
              <Droplets className="h-4 w-4" aria-hidden />
              Выпить воды 100 мл
            </button>
          </div>
        </div>
      </div>

      <TakeAdditiveModal
        open={takeOpen}
        accessToken={accessToken}
        dateYmd={dateYmd}
        onClose={() => setTakeOpen(false)}
        onSaved={() => {
          void load();
          onChanged();
        }}
      />
    </>
  );
}
