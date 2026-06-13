import { ClipboardList, Shield, SlidersHorizontal, UsersRound } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

import {
  cancelSubscription,
  createAdminCuratorAssignment,
  createAdminPlan,
  deleteAdminCuratorAssignment,
  deleteAdminPlan,
  deleteAdminUser,
  deletePlanFeature,
  getAdminCuratorAssignments,
  getAdminCurators,
  getAdminPlans,
  getAdminSubscriptions,
  getAdminUser,
  getAdminUsers,
  getNutritionPipelineSettings,
  grantSubscription,
  updateAdminPlan,
  updateAdminUser,
  updateNutritionPipelineSettings,
  upsertPlanFeature,
  upsertUserFeatureOverride,
  type AdminGlobalNutritionPipeline,
  type AdminCuratorUserAssignment,
  type AdminNutritionPipelineSettings,
  type AdminPlan,
  type AdminPlanFeaturePayload,
  type AdminSubscription,
  type AdminUser,
  type AdminUserDetail,
  type AdminUserNutritionPipeline,
  type AdminUserOverridePayload,
} from "../api/adminApi";
import {
  emptyFeature,
  emptyOverride,
  FEATURE_PRESETS,
  featureOptionLabel,
  getDefaultFeaturePayload,
} from "../admin/featurePresets";
import { AdminConfirmDialog } from "../components/admin/AdminConfirmDialog";
import { SwipeableUserRow } from "../components/admin/SwipeableUserRow";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";

type TabKey = "users" | "curators" | "plans" | "subscriptions";

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function userLabel(user: AdminUser | AdminUserDetail) {
  return user.email || user.first_name || user.username || `ID ${user.id}`;
}

function errorMessage(err: unknown, fallback: string) {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg ?? JSON.stringify(item)).join("; ");
    }
    if (detail) {
      return String(detail);
    }
    return err.message || fallback;
  }
  return err instanceof Error ? err.message : fallback;
}

const globalPipelineLabels: Record<AdminGlobalNutritionPipeline, string> = {
  v1_csv: "V1 — nutrition.csv",
  v2_usda: "V2 — USDA FoodData Central",
};

const userPipelineLabels: Record<AdminUserNutritionPipeline, string> = {
  global: "Как у всех",
  v1_csv: "V1",
  v2_usda: "V2",
};

export function AdminPage() {
  const navigate = useNavigate();
  const { user, logout, validateSession, getAccessToken } = useAuth();
  const [tab, setTab] = useState<TabKey>("users");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null);
  const [nutritionPipelineSettings, setNutritionPipelineSettings] = useState<AdminNutritionPipelineSettings | null>(null);
  const [plans, setPlans] = useState<AdminPlan[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [planFormMode, setPlanFormMode] = useState<"create" | "edit">("create");
  const [deleteConfirmUser, setDeleteConfirmUser] = useState<AdminUser | null>(null);
  const [deleteConfirmPlan, setDeleteConfirmPlan] = useState(false);
  const [featureForm, setFeatureForm] = useState<AdminPlanFeaturePayload>(emptyFeature);
  const [overrideForm, setOverrideForm] = useState<AdminUserOverridePayload>(emptyOverride);
  const [grantPlanId, setGrantPlanId] = useState<number | "">("");
  const [grantDays, setGrantDays] = useState("");
  const [curators, setCurators] = useState<AdminUser[]>([]);
  const [curatorAssignments, setCuratorAssignments] = useState<AdminCuratorUserAssignment[]>([]);
  const [selectedCuratorId, setSelectedCuratorId] = useState<number | null>(null);
  const [assignUserId, setAssignUserId] = useState<number | "">("");
  const [planForm, setPlanForm] = useState({
    code: "",
    name: "",
    description: "",
    price_amount: 0,
    currency: "RUB",
    period_days: 30,
    is_active: true,
    sort_order: 100,
  });

  const token = getAccessToken();
  const avatarFallback = user?.first_name?.[0] ?? user?.email?.[0] ?? "A";
  const selectedPlan = useMemo(
    () =>
      planFormMode === "edit" ? (plans.find((plan) => plan.id === selectedPlanId) ?? null) : null,
    [plans, selectedPlanId, planFormMode],
  );

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const ok = await validateSession();
    const currentToken = getAccessToken();
    if (!ok || !currentToken) {
      navigate("/login", { replace: true });
      return;
    }
    try {
      const [usersResult, plansResult, subscriptionsResult, nutritionPipelineResult] = await Promise.allSettled([
        getAdminUsers(currentToken, { q: query || undefined }),
        getAdminPlans(currentToken),
        getAdminSubscriptions(currentToken),
        getNutritionPipelineSettings(currentToken),
      ]);

      if (usersResult.status === "fulfilled") {
        setUsers(usersResult.value);
      }
      if (plansResult.status === "fulfilled") {
        setPlans(plansResult.value);
      }
      if (subscriptionsResult.status === "fulfilled") {
        setSubscriptions(subscriptionsResult.value);
      }
      if (nutritionPipelineResult.status === "fulfilled") {
        setNutritionPipelineSettings(nutritionPipelineResult.value);
      }

      const failed = [usersResult, plansResult, subscriptionsResult, nutritionPipelineResult].filter(
        (result) => result.status === "rejected",
      );
      if (failed.length > 0) {
        setError("Часть данных админки не загрузилась. Пользователи и тарифы показываются независимо от подписок.");
      }
    } catch (err) {
      setError(errorMessage(err, "Не удалось загрузить админку"));
    } finally {
      setLoading(false);
    }
  }, [getAccessToken, navigate, query, validateSession]);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

  const loadCuratorsTab = useCallback(async () => {
    if (!token) return;
    try {
      const [curatorsList, assignments] = await Promise.all([
        getAdminCurators(token),
        getAdminCuratorAssignments(
          token,
          selectedCuratorId != null ? { curator_id: selectedCuratorId } : undefined,
        ),
      ]);
      setCurators(curatorsList);
      setCuratorAssignments(assignments);
      if (selectedCuratorId == null && curatorsList.length > 0) {
        setSelectedCuratorId(curatorsList[0].id);
      }
    } catch (err) {
      setError(errorMessage(err, "Не удалось загрузить кураторов"));
    }
  }, [selectedCuratorId, token]);

  useEffect(() => {
    if (tab !== "curators" || !token) return;
    void loadCuratorsTab();
  }, [loadCuratorsTab, tab, token]);

  const assignableUsers = useMemo(
    () =>
      users.filter(
        (u) =>
          u.role === "user" &&
          u.id !== selectedCuratorId &&
          !curatorAssignments.some((a) => a.user_id === u.id),
      ),
    [curatorAssignments, selectedCuratorId, users],
  );

  const refreshUserDetail = useCallback(
    async (userId: number) => {
      if (!token) return;
      const detail = await getAdminUser(token, userId);
      setSelectedUser(detail);
    },
    [token],
  );

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const runAction = async (action: () => Promise<void>) => {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      await action();
      await loadAdminData();
    } catch (err) {
      setError(errorMessage(err, "Не удалось выполнить действие"));
    } finally {
      setSaving(false);
    }
  };

  const selectUser = (adminUser: AdminUser) => {
    void runAction(async () => {
      await refreshUserDetail(adminUser.id);
      setTab("users");
    });
  };

  const savePlan = () => {
    void runAction(async () => {
      if (!token) return;
      if (planFormMode === "edit" && selectedPlanId) {
        await updateAdminPlan(token, selectedPlanId, planForm);
      } else {
        const created = await createAdminPlan(token, planForm);
        setPlanFormMode("edit");
        setSelectedPlanId(created.id);
      }
    });
  };

  const editPlan = (plan: AdminPlan) => {
    setPlanFormMode("edit");
    setSelectedPlanId(plan.id);
    setPlanForm({
      code: plan.code,
      name: plan.name,
      description: plan.description ?? "",
      price_amount: plan.price_amount,
      currency: plan.currency,
      period_days: plan.period_days,
      is_active: plan.is_active,
      sort_order: plan.sort_order,
    });
  };

  const resetPlanForm = () => {
    setPlanFormMode("create");
    setSelectedPlanId(null);
    setPlanForm({
      code: "",
      name: "",
      description: "",
      price_amount: 0,
      currency: "RUB",
      period_days: 30,
      is_active: true,
      sort_order: 100,
    });
  };

  const confirmDeleteUser = () => {
    if (!deleteConfirmUser) return;
    const target = deleteConfirmUser;
    void runAction(async () => {
      if (!token) return;
      await deleteAdminUser(token, target.id);
      if (selectedUser?.id === target.id) {
        setSelectedUser(null);
      }
      setDeleteConfirmUser(null);
    });
  };

  const confirmDeletePlan = () => {
    if (!selectedPlanId) return;
    const planId = selectedPlanId;
    void runAction(async () => {
      if (!token) return;
      const result = await deleteAdminPlan(token, planId);
      const fullyDeleted =
        result !== null &&
        typeof result === "object" &&
        "deleted" in result &&
        Boolean((result as { deleted?: boolean }).deleted);
      if (!fullyDeleted) {
        setError("Тариф привязан к подпискам и был деактивирован вместо удаления.");
      }
      resetPlanForm();
      setDeleteConfirmPlan(false);
    });
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <p className="text-base text-slate-500">Загружаем админку...</p>
      </div>
    );
  }

  return (
    <AppShell activeNav="home" avatarFallback={avatarFallback} onLogout={handleLogout} showMobileFab={false}>
      <div className="mx-auto max-w-7xl space-y-6 p-4 lg:p-8">
        <header className="rounded-3xl border border-green-100 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-green-700">Meal Mentor</p>
              <h1 className="mt-2 text-3xl font-bold text-slate-950">Админка Meal Mentor</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">
                Пользователи, тарифы, подписки и ручные права в одном месте.
              </p>
              <div className="mt-4 max-w-md rounded-2xl border border-green-100 bg-green-50 p-3">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-green-800">
                  NutritionService для всех пользователей
                </label>
                <select
                  value={nutritionPipelineSettings?.global_version ?? "v1_csv"}
                  disabled={saving || !nutritionPipelineSettings}
                  onChange={(event) => {
                    const nextValue = event.target.value as AdminGlobalNutritionPipeline;
                    void runAction(async () => {
                      if (!token) return;
                      await updateNutritionPipelineSettings(token, { global_version: nextValue });
                    });
                  }}
                  className="mt-2 w-full rounded-xl border border-green-100 bg-white px-3 py-2 text-sm font-semibold text-slate-800"
                >
                  <option value="v1_csv">{globalPipelineLabels.v1_csv}</option>
                  <option value="v2_usda">{globalPipelineLabels.v2_usda}</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 rounded-2xl bg-green-50 p-1 text-sm font-semibold text-slate-700 sm:grid-cols-4">
              {([
                ["users", "Пользователи", UsersRound],
                ["curators", "Кураторы", ClipboardList],
                ["plans", "Тарифы", SlidersHorizontal],
                ["subscriptions", "Подписки", Shield],
              ] as const).map(([key, label, Icon]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setTab(key)}
                  className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 transition ${
                    tab === key ? "bg-white text-green-700 shadow-sm" : "text-slate-600 hover:text-green-700"
                  }`}
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  <span className="hidden sm:inline">{label}</span>
                </button>
              ))}
            </div>
          </div>
          {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
        </header>

        {tab === "users" ? (
          <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Поиск: email, имя, username, provider"
                  className="min-w-0 flex-1 rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-green-500"
                />
                <button
                  type="button"
                  onClick={() => void loadAdminData()}
                  className="rounded-2xl bg-green-600 px-5 py-3 text-sm font-semibold text-white hover:bg-green-700"
                >
                  Найти
                </button>
              </div>
              <div className="mt-4 md:overflow-visible">
                <table className="w-full table-fixed text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th className="w-[38%] px-2 py-2 md:px-3">Пользователь</th>
                      <th className="hidden w-[14%] px-2 py-2 md:table-cell md:px-3">Provider</th>
                      <th className="hidden w-[10%] px-2 py-2 md:table-cell md:px-3">Роль</th>
                      <th className="hidden w-[10%] px-2 py-2 md:table-cell md:px-3">Статус</th>
                      <th className="w-[22%] px-2 py-2 md:w-[14%] md:px-3">Подписка</th>
                      <th className="w-[40%] px-2 py-2 md:w-[14%] md:px-3">Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((adminUser) => (
                      <tr key={adminUser.id}>
                        <td colSpan={6} className="p-0">
                          <SwipeableUserRow
                            disabled={saving || adminUser.role === "admin" || adminUser.id === user?.id}
                            onDeleteRequest={() => setDeleteConfirmUser(adminUser)}
                          >
                            <div className="flex w-full text-left text-sm">
                              <div className="w-[38%] shrink-0 px-2 py-3 md:px-3">
                                <button
                                  type="button"
                                  onClick={() => selectUser(adminUser)}
                                  className="max-w-full truncate text-left font-semibold text-green-700"
                                >
                                  {userLabel(adminUser)}
                                </button>
                                <p className="truncate text-xs text-slate-500">{adminUser.email || "—"}</p>
                                <p className="text-[11px] text-slate-400">ID {adminUser.id}</p>
                              </div>
                              <div className="hidden w-[14%] truncate px-2 py-3 md:block md:px-3">
                                {adminUser.provider || "—"}
                              </div>
                              <div className="hidden w-[10%] px-2 py-3 md:block md:px-3">{adminUser.role}</div>
                              <div className="hidden w-[10%] px-2 py-3 md:block md:px-3">{adminUser.status}</div>
                              <div className="w-[22%] truncate px-2 py-3 md:w-[14%] md:px-3">
                                {adminUser.subscription_status}
                              </div>
                              <div className="w-[40%] px-2 py-3 md:w-[14%] md:px-3">
                                <div className="flex flex-wrap gap-2">
                                  <select
                                    value={adminUser.role}
                                    disabled={saving || adminUser.id === user?.id}
                                    onChange={(e) => {
                                      const nextRole = e.target.value as "user" | "curator" | "admin";
                                      void runAction(async () => {
                                        if (!token) return;
                                        await updateAdminUser(token, adminUser.id, { role: nextRole });
                                      });
                                    }}
                                    className="rounded-full border border-green-200 bg-white px-2 py-1 text-xs font-semibold text-green-700"
                                  >
                                    <option value="user">user</option>
                                    <option value="curator">curator</option>
                                    <option value="admin">admin</option>
                                  </select>
                                  <select
                                    value={adminUser.nutrition_pipeline_version}
                                    disabled={saving}
                                    onChange={(e) => {
                                      const nextValue = e.target.value as AdminUserNutritionPipeline;
                                      void runAction(async () => {
                                        if (!token) return;
                                        await updateAdminUser(token, adminUser.id, {
                                          nutrition_pipeline_version: nextValue,
                                        });
                                        if (selectedUser?.id === adminUser.id) {
                                          await refreshUserDetail(adminUser.id);
                                        }
                                      });
                                    }}
                                    className="rounded-full border border-sky-200 bg-white px-2 py-1 text-xs font-semibold text-sky-700"
                                    title="NutritionService"
                                  >
                                    <option value="global">Как у всех</option>
                                    <option value="v1_csv">V1</option>
                                    <option value="v2_usda">V2</option>
                                  </select>
                                  <button
                                    type="button"
                                    disabled={saving}
                                    onClick={() =>
                                      void runAction(async () => {
                                        if (!token) return;
                                        await updateAdminUser(token, adminUser.id, {
                                          status: adminUser.status === "blocked" ? "active" : "blocked",
                                        });
                                      })
                                    }
                                    className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                                  >
                                    {adminUser.status === "blocked" ? "Разблокировать" : "Заблокировать"}
                                  </button>
                                </div>
                              </div>
                            </div>
                          </SwipeableUserRow>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <aside className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              {selectedUser ? (
                <div className="space-y-5">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-green-700">Пользователь</p>
                    <h2 className="mt-1 text-xl font-bold text-slate-950">{userLabel(selectedUser)}</h2>
                    <p className="text-sm text-slate-500">ID {selectedUser.id}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <Info label="Роль" value={selectedUser.role} />
                    <Info label="Статус" value={selectedUser.status} />
                    <Info label="Provider" value={selectedUser.provider || "—"} />
                    <Info label="Подписка" value={selectedUser.subscription_status} />
                    <Info label="NutritionService" value={selectedUser.nutrition_pipeline_version} />
                    <Info label="Создан" value={formatDate(selectedUser.created_at)} />
                    <Info label="Активна до" value={formatDate(selectedUser.active_subscription_ends_at)} />
                  </div>

                  <div className="space-y-2 rounded-2xl bg-sky-50 p-3">
                    <p className="font-semibold text-slate-900">NutritionService для пользователя</p>
                    <select
                      value={selectedUser.nutrition_pipeline_version}
                      disabled={saving}
                      onChange={(event) => {
                        const nextValue = event.target.value as AdminUserNutritionPipeline;
                        void runAction(async () => {
                          if (!token) return;
                          await updateAdminUser(token, selectedUser.id, {
                            nutrition_pipeline_version: nextValue,
                          });
                          await refreshUserDetail(selectedUser.id);
                        });
                      }}
                      className="w-full rounded-xl border border-sky-100 bg-white px-3 py-2 text-sm font-semibold text-slate-800"
                    >
                      <option value="global">{userPipelineLabels.global}</option>
                      <option value="v1_csv">{userPipelineLabels.v1_csv}</option>
                      <option value="v2_usda">{userPipelineLabels.v2_usda}</option>
                    </select>
                  </div>

                  <div className="space-y-2 rounded-2xl bg-green-50 p-3">
                    <p className="font-semibold text-slate-900">Выдать подписку</p>
                    <select
                      value={grantPlanId}
                      onChange={(event) => setGrantPlanId(event.target.value ? Number(event.target.value) : "")}
                      className="w-full rounded-xl border border-green-100 px-3 py-2 text-sm"
                    >
                      <option value="">Выберите тариф</option>
                      {plans.map((plan) => (
                        <option key={plan.id} value={plan.id}>
                          {plan.name} ({plan.code})
                        </option>
                      ))}
                    </select>
                    <input
                      value={grantDays}
                      onChange={(event) => setGrantDays(event.target.value)}
                      inputMode="numeric"
                      placeholder="Дней, пусто = период тарифа"
                      className="w-full rounded-xl border border-green-100 px-3 py-2 text-sm"
                    />
                    <button
                      type="button"
                      disabled={!grantPlanId || saving}
                      onClick={() =>
                        void runAction(async () => {
                          if (!token || !grantPlanId) return;
                          await grantSubscription(token, selectedUser.id, {
                            plan_id: Number(grantPlanId),
                            days: grantDays ? Number(grantDays) : undefined,
                          });
                          await refreshUserDetail(selectedUser.id);
                        })
                      }
                      className="w-full rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      Выдать подписку
                    </button>
                  </div>

                  <div className="space-y-2 rounded-2xl bg-slate-50 p-3">
                    <p className="font-semibold text-slate-900">Ручной override</p>
                    <FeatureValueForm value={overrideForm} onChange={setOverrideForm} includeReason />
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() =>
                        void runAction(async () => {
                          if (!token) return;
                          await upsertUserFeatureOverride(token, selectedUser.id, overrideForm.feature_key, overrideForm);
                          await refreshUserDetail(selectedUser.id);
                        })
                      }
                      className="w-full rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                    >
                      Сохранить override
                    </button>
                    <div className="space-y-1 pt-2">
                      {selectedUser.feature_overrides.map((override) => (
                        <p key={override.id} className="rounded-xl bg-white px-3 py-2 text-xs text-slate-600">
                          <span className="font-semibold text-slate-900">{override.feature_key}</span>: {override.value_bool ?? override.value_int ?? override.value_text ?? "—"}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Выберите пользователя, чтобы открыть детали, подписки и ручные права.</p>
              )}
            </aside>
          </section>
        ) : null}

        {tab === "curators" ? (
          <section className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-green-700">Кураторы</p>
              <p className="mt-1 text-sm text-slate-500">Пользователи с ролью curator или admin.</p>
              <ul className="mt-4 space-y-1">
                {curators.length === 0 ? (
                  <li className="text-sm text-slate-500">
                    Нет кураторов и администраторов. Назначьте роль curator или используйте существующих admin.
                  </li>
                ) : (
                  curators.map((curator) => (
                    <li key={curator.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedCuratorId(curator.id);
                          setAssignUserId("");
                        }}
                        className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${
                          selectedCuratorId === curator.id
                            ? "bg-green-50 font-semibold text-green-800"
                            : "text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        <span className="block truncate">{userLabel(curator)}</span>
                        <span className="text-xs text-slate-500">{curator.role}</span>
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              {selectedCuratorId == null ? (
                <p className="text-sm text-slate-500">Выберите куратора слева.</p>
              ) : (
                <div className="space-y-5">
                  <div>
                    <h2 className="text-xl font-bold text-slate-950">
                      {(() => {
                        const selected = curators.find((c) => c.id === selectedCuratorId);
                        return selected ? userLabel(selected) : `ID ${selectedCuratorId}`;
                      })()}
                    </h2>
                    <p className="text-sm text-slate-500">Привязанные пользователи</p>
                  </div>

                  <ul className="divide-y divide-slate-100 rounded-2xl border border-slate-100">
                    {curatorAssignments.length === 0 ? (
                      <li className="px-4 py-6 text-center text-sm text-slate-500">Нет привязанных пользователей.</li>
                    ) : (
                      curatorAssignments.map((assignment) => (
                        <li
                          key={assignment.id}
                          className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm"
                        >
                          <div className="min-w-0">
                            <p className="font-semibold text-slate-900">
                              {assignment.user_name || assignment.user_email || `ID ${assignment.user_id}`}
                            </p>
                            <p className="truncate text-xs text-slate-500">{assignment.user_email || "—"}</p>
                          </div>
                          <button
                            type="button"
                            disabled={saving}
                            onClick={() =>
                              void runAction(async () => {
                                if (!token) return;
                                await deleteAdminCuratorAssignment(token, assignment.id);
                                await loadCuratorsTab();
                              })
                            }
                            className="rounded-full border border-red-200 px-3 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
                          >
                            Удалить
                          </button>
                        </li>
                      ))
                    )}
                  </ul>

                  <div className="space-y-3 rounded-2xl bg-green-50 p-4">
                    <p className="font-semibold text-slate-900">Привязать пользователя</p>
                    <select
                      value={assignUserId}
                      onChange={(e) => setAssignUserId(e.target.value ? Number(e.target.value) : "")}
                      className="w-full rounded-xl border border-green-100 bg-white px-3 py-2 text-sm"
                    >
                      <option value="">Выберите пользователя</option>
                      {assignableUsers.map((u) => (
                        <option key={u.id} value={u.id}>
                          {userLabel(u)} ({u.email || `ID ${u.id}`})
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={saving || assignUserId === ""}
                      onClick={() =>
                        void runAction(async () => {
                          if (!token || assignUserId === "" || selectedCuratorId == null) return;
                          await createAdminCuratorAssignment(token, {
                            curator_id: selectedCuratorId,
                            user_id: assignUserId,
                          });
                          setAssignUserId("");
                          await loadCuratorsTab();
                        })
                      }
                      className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      Привязать
                    </button>
                  </div>
                </div>
              )}
            </div>
          </section>
        ) : null}

        {tab === "plans" ? (
          <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
              {plans.map((plan) => (
                <button
                  key={plan.id}
                  type="button"
                  onClick={() => editPlan(plan)}
                  className={`rounded-2xl border bg-white p-3 text-left shadow-sm transition hover:border-green-300 ${
                    planFormMode === "edit" && selectedPlanId === plan.id
                      ? "border-green-500 ring-1 ring-green-200"
                      : "border-slate-200"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-slate-950">{plan.name}</p>
                      <p className="truncate text-xs text-slate-500">{plan.code}</p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        plan.is_active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {plan.is_active ? "active" : "off"}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2 text-xs text-slate-600">
                    <span>
                      {plan.price_amount} {plan.currency}
                    </span>
                    <span>{plan.period_days} дн.</span>
                    <span>{plan.features.length} фич</span>
                  </div>
                </button>
              ))}
            </div>

            <aside className="space-y-4 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-bold text-slate-950">
                  {planFormMode === "edit" && selectedPlan
                    ? `Редактирование тарифа: ${selectedPlan.name}`
                    : "Создание нового тарифа"}
                </h2>
                <button type="button" onClick={resetPlanForm} className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                  + Новый тариф
                </button>
              </div>
              <div className="grid gap-2">
                <input value={planForm.code} onChange={(e) => setPlanForm({ ...planForm, code: e.target.value })} placeholder="code" className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                <input value={planForm.name} onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })} placeholder="Название" className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                <textarea value={planForm.description} onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })} placeholder="Описание" className="min-h-20 rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                <div className="grid grid-cols-2 gap-2">
                  <input value={planForm.price_amount} onChange={(e) => setPlanForm({ ...planForm, price_amount: Number(e.target.value) })} type="number" className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                  <input value={planForm.currency} onChange={(e) => setPlanForm({ ...planForm, currency: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                  <input value={planForm.period_days} onChange={(e) => setPlanForm({ ...planForm, period_days: Number(e.target.value) })} type="number" className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                  <input value={planForm.sort_order} onChange={(e) => setPlanForm({ ...planForm, sort_order: Number(e.target.value) })} type="number" className="rounded-xl border border-slate-200 px-3 py-2 text-sm" />
                </div>
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <input type="checkbox" checked={planForm.is_active} onChange={(e) => setPlanForm({ ...planForm, is_active: e.target.checked })} />
                  Активен
                </label>
                <button type="button" disabled={saving || !planForm.code || !planForm.name} onClick={savePlan} className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50">
                  Сохранить тариф
                </button>
                {planFormMode === "edit" && selectedPlanId ? (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => setDeleteConfirmPlan(true)}
                    className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
                  >
                    Удалить тариф
                  </button>
                ) : null}
              </div>

              {selectedPlan ? (
                <div className="space-y-3 rounded-2xl bg-slate-50 p-3">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-900">Features</p>
                    <button
                      type="button"
                      onClick={() =>
                        void runAction(async () => {
                          if (!selectedPlan || !token) return;
                          await updateAdminPlan(token, selectedPlan.id, { is_active: !selectedPlan.is_active });
                        })
                      }
                      className="text-xs font-semibold text-green-700"
                    >
                      {selectedPlan.is_active ? "Деактивировать" : "Активировать"}
                    </button>
                  </div>
                  <FeatureValueForm value={featureForm} onChange={setFeatureForm} />
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() =>
                      void runAction(async () => {
                        if (!token || !selectedPlan) return;
                        await upsertPlanFeature(token, selectedPlan.id, featureForm.feature_key, featureForm);
                      })
                    }
                    className="w-full rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                  >
                    Сохранить feature
                  </button>
                  <div className="space-y-2">
                    {selectedPlan.features.map((feature) => (
                      <div key={feature.id} className="rounded-xl bg-white p-3 text-xs text-slate-600">
                        <div className="flex items-center justify-between gap-2">
                          <button type="button" onClick={() => setFeatureForm(feature)} className="text-left font-semibold text-slate-950">
                            {feature.feature_key}
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              void runAction(async () => {
                                if (!token) return;
                                await deletePlanFeature(token, selectedPlan.id, feature.id);
                              })
                            }
                            className="text-red-600"
                          >
                            Удалить
                          </button>
                        </div>
                        <p>{feature.feature_name}: {feature.value_bool ?? feature.value_int ?? feature.value_text ?? "—"}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </aside>
          </section>
        ) : null}

        {tab === "subscriptions" ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-[820px] w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">ID</th>
                    <th className="px-3 py-2">User</th>
                    <th className="px-3 py-2">Plan</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Provider</th>
                    <th className="px-3 py-2">Payment</th>
                    <th className="px-3 py-2">Start</th>
                    <th className="px-3 py-2">End</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((sub) => (
                    <tr key={sub.id} className="border-t border-slate-100">
                      <td className="px-3 py-3 font-semibold">{sub.id}</td>
                      <td className="px-3 py-3">{sub.user_email || sub.user_name || sub.user_id}</td>
                      <td className="px-3 py-3">{sub.plan_name || sub.plan}</td>
                      <td className="px-3 py-3">{sub.status}</td>
                      <td className="px-3 py-3">{sub.provider}</td>
                      <td className="px-3 py-3">{sub.payment_status}</td>
                      <td className="px-3 py-3">{formatDate(sub.started_at)}</td>
                      <td className="px-3 py-3">{formatDate(sub.ends_at)}</td>
                      <td className="px-3 py-3">
                        <button
                          type="button"
                          disabled={sub.status === "cancelled" || saving}
                          onClick={() =>
                            void runAction(async () => {
                              if (!token) return;
                              await cancelSubscription(token, sub.id);
                            })
                          }
                          className="rounded-full border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40"
                        >
                          Cancel
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>

      <AdminConfirmDialog
        open={deleteConfirmUser !== null}
        title="Удаление пользователя"
        message="Вы уверены, что хотите удалить пользователя?"
        onConfirm={confirmDeleteUser}
        onCancel={() => setDeleteConfirmUser(null)}
        loading={saving}
      />

      <AdminConfirmDialog
        open={deleteConfirmPlan}
        title="Удаление тарифа"
        message={
          selectedPlan
            ? `Удалить тариф «${selectedPlan.name}»? Если есть подписки, тариф будет только деактивирован.`
            : "Удалить выбранный тариф?"
        }
        onConfirm={confirmDeletePlan}
        onCancel={() => setDeleteConfirmPlan(false)}
        loading={saving}
      />
    </AppShell>
  );
}

function Info({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-words font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function FeatureValueForm<T extends AdminPlanFeaturePayload | AdminUserOverridePayload>({
  value,
  onChange,
  includeReason = false,
}: {
  value: T;
  onChange: (value: T) => void;
  includeReason?: boolean;
}) {
  const setValue = (patch: Partial<T>) => onChange({ ...value, ...patch });
  return (
    <div className="grid gap-2">
      <select
        value={value.feature_key}
        onChange={(event) => {
          const key = event.target.value;
          const defaults = getDefaultFeaturePayload(key);
          if ("feature_name" in value) {
            onChange({
              ...value,
              ...defaults,
              reason: "reason" in value ? value.reason : undefined,
            } as T);
          } else {
            onChange({
              ...value,
              feature_key: key,
              value_type: defaults.value_type,
              value_bool: defaults.value_bool,
              value_int: defaults.value_int,
              value_text: defaults.value_text,
              reason: "reason" in value ? value.reason : undefined,
            } as T);
          }
        }}
        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
      >
        {FEATURE_PRESETS.map((key) => (
          <option key={key} value={key}>
            {featureOptionLabel(key)}
          </option>
        ))}
      </select>
      {"feature_name" in value ? (
        <input
          value={value.feature_name}
          onChange={(event) => setValue({ feature_name: event.target.value } as unknown as Partial<T>)}
          placeholder="Название feature"
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
        />
      ) : null}
      <select
        value={value.value_type}
        onChange={(event) => setValue({ value_type: event.target.value as "boolean" | "limit" | "text" } as Partial<T>)}
        className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
      >
        <option value="boolean">boolean</option>
        <option value="limit">limit</option>
        <option value="text">text</option>
      </select>
      {value.value_type === "boolean" ? (
        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <input type="checkbox" checked={Boolean(value.value_bool)} onChange={(event) => setValue({ value_bool: event.target.checked } as Partial<T>)} />
          Включено
        </label>
      ) : null}
      {value.value_type === "limit" ? (
        <input
          type="number"
          value={value.value_int ?? 0}
          onChange={(event) => setValue({ value_int: Number(event.target.value) } as Partial<T>)}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
        />
      ) : null}
      {value.value_type === "text" ? (
        <textarea
          value={value.value_text ?? ""}
          onChange={(event) => setValue({ value_text: event.target.value } as Partial<T>)}
          className="min-h-20 rounded-xl border border-slate-200 px-3 py-2 text-sm"
        />
      ) : null}
      {includeReason && "reason" in value ? (
        <input
          value={value.reason ?? ""}
          onChange={(event) => setValue({ reason: event.target.value } as unknown as Partial<T>)}
          placeholder="Причина"
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
        />
      ) : null}
    </div>
  );
}
