import { useCallback, useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";

import { deleteAdditive, listAdditives } from "../../api/additivesApi";
import type { AdditiveItem } from "../../types/additives";
import { SwipeDeleteRow } from "../common/SwipeDeleteRow";
import { EditAdditiveModal } from "./EditAdditiveModal";

type Props = {
  open: boolean;
  accessToken: string;
  onClose: () => void;
  onChanged: () => void;
};

export function AdditivesListModal({ open, accessToken, onClose, onChanged }: Props) {
  const [items, setItems] = useState<AdditiveItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AdditiveItem | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAdditives(accessToken);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить список");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (open) void load();
  }, [open, load]);

  const handleDelete = async (id: number) => {
    if (deletingId != null) return;
    setDeletingId(id);
    try {
      await deleteAdditive(accessToken, id);
      await load();
      onChanged();
    } finally {
      setDeletingId(null);
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
          className="flex max-h-[min(85vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h2 className="text-lg font-semibold text-slate-900">Мои добавки</h2>
            <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100">
              <X className="h-5 w-5" aria-hidden />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-green-600" aria-hidden />
              </div>
            ) : null}
            {error ? <p className="p-4 text-sm text-red-600">{error}</p> : null}
            {!loading && items.length === 0 ? (
              <p className="p-8 text-center text-sm text-slate-500">Добавок пока нет.</p>
            ) : null}
            {items.map((item) => (
              <SwipeDeleteRow
                key={item.id}
                disabled={deletingId === item.id}
                onDelete={() => void handleDelete(item.id)}
                onOpen={() => setEditing(item)}
              >
                <div className="flex items-center gap-3 px-4 py-3">
                  {item.photo_thumb_url ? (
                    <img src={item.photo_thumb_url} alt="" className="h-12 w-12 rounded-lg object-cover" />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-100 text-xs text-slate-400">
                      —
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-slate-900 truncate">{item.additive_name}</p>
                    {item.serving_label ? (
                      <p className="text-xs text-slate-500 truncate">{item.serving_label}</p>
                    ) : null}
                  </div>
                </div>
              </SwipeDeleteRow>
            ))}
          </div>
        </div>
      </div>

      <EditAdditiveModal
        open={editing != null}
        accessToken={accessToken}
        additive={editing}
        onClose={() => setEditing(null)}
        onSaved={() => {
          void load();
          onChanged();
        }}
      />
    </>
  );
}
