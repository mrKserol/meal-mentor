import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import { getCuratorUsers, type CuratorUserListItem } from "../api/curatorApi";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";

function userLabel(u: CuratorUserListItem): string {
  return u.first_name || u.username || u.email || `ID ${u.id}`;
}

export function CuratorPage() {
  const navigate = useNavigate();
  const { user, validateSession, logout, getAccessToken } = useAuth();
  const [items, setItems] = useState<CuratorUserListItem[]>([]);
  const [phase, setPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setPhase("loading");
    setError(null);
    try {
      const ok = await validateSession();
      const token = getAccessToken();
      if (!ok || !token) {
        navigate("/login", { replace: true });
        return;
      }
      const rows = await getCuratorUsers(token);
      setItems(rows);
      setPhase("ready");
    } catch (e) {
      const message =
        axios.isAxiosError(e) && e.response?.data?.detail != null
          ? String(e.response.data.detail)
          : e instanceof Error
            ? e.message
            : "Не удалось загрузить список пользователей";
      setError(message);
      setPhase("error");
    }
  }, [getAccessToken, navigate, validateSession]);

  useEffect(() => {
    if (user) void load();
  }, [user?.id, load]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  return (
    <AppShell activeNav="home" avatarFallback={avatarFallback} onLogout={handleLogout} showMobileFab={false}>
      <div className="mx-auto w-full max-w-3xl p-4 pb-8 lg:p-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Режим куратора</h1>
          <p className="mt-1 text-sm text-slate-600">
            {user?.role === "admin"
              ? "Просмотр дневников пользователей (read-only)."
              : "Пользователи, закреплённые за вами."}
          </p>
        </header>

        {phase === "loading" ? <p className="text-slate-500">Загрузка…</p> : null}
        {phase === "error" && error ? (
          <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        ) : null}

        {phase === "ready" && items.length === 0 ? (
          <p className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            Пока нет привязанных пользователей.
          </p>
        ) : null}

        <ul className="space-y-3">
          {items.map((u) => (
            <li key={u.id}>
              <button
                type="button"
                onClick={() => navigate(`/curator/users/${u.id}`)}
                className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-green-200 hover:bg-green-50/30"
              >
                <p className="text-lg font-semibold text-slate-900">{userLabel(u)}</p>
                <p className="mt-1 text-sm text-slate-500">{u.email || "—"}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>ID {u.id}</span>
                  <span>·</span>
                  <span>{u.status}</span>
                  <span>·</span>
                  <span>{u.subscription_status}</span>
                  {u.weight_kg != null ? (
                    <>
                      <span>·</span>
                      <span>{u.weight_kg} кг</span>
                    </>
                  ) : null}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
