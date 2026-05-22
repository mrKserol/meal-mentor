import { useState } from "react";
import { Pill } from "lucide-react";

import { useAuth } from "../../hooks/useAuth";
import { AdditivesListModal } from "./AdditivesListModal";
import { CreateAdditiveModal } from "./CreateAdditiveModal";

export function AdditivesProfileBlock() {
  const { getAccessToken } = useAuth();
  const token = getAccessToken();
  const [createOpen, setCreateOpen] = useState(false);
  const [listOpen, setListOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  if (!token) return null;

  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <>
      <div className="min-w-0 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <div className="mb-6 flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-violet-50">
            <Pill className="h-6 w-6 text-violet-600" aria-hidden />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Мои добавки</h2>
            <p className="text-sm text-slate-500">Добавки, которые можно быстро отмечать в дневнике.</p>
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-green-700"
          >
            Создать
          </button>
          <button
            type="button"
            onClick={() => setListOpen(true)}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
          >
            Посмотреть все
          </button>
        </div>
      </div>

      <CreateAdditiveModal
        open={createOpen}
        accessToken={token}
        onClose={() => setCreateOpen(false)}
        onSaved={bump}
      />
      <AdditivesListModal
        key={refreshKey}
        open={listOpen}
        accessToken={token}
        onClose={() => setListOpen(false)}
        onChanged={bump}
      />
    </>
  );
}
