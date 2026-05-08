import { Shield, SlidersHorizontal, UsersRound } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  cancelSubscription,
  createAdminPlan,
  deletePlanFeature,
  getAdminPlans,
  getAdminSubscriptions,
  getAdminUser,
  getAdminUsers,
  grantSubscription,
  updateAdminPlan,
  updateAdminUser,
  upsertPlanFeature,
  upsertUserFeatureOverride,
  type AdminPlan,
  type AdminPlanFeaturePayload,
  type AdminSubscription,
  type AdminUser,
  type AdminUserDetail,
  type AdminUserOverridePayload,
} from "../api/adminApi";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";

const FEATURE_PRESETS = [
  "ai_chat_enabled",
  "food_photo_recognition_enabled",
  "label_analysis_enabled",
  "daily_ai_requests_limit",
  "monthly_photo_recognition_limit",
  "monthly_label_analysis_limit",
  "nutrition_diary_enabled",
  "advanced_nutrients_enabled",
];

type TabKey = "users" | "plans" | "subscriptions";

const emptyFeature: AdminPlanFeaturePayload = {
  feature_key: "ai_chat_enabled",
  feature_name: "ИИ-чат",
  value_type: "boolean",
  value_bool: true,
  value_int: null,
  value_text: null,
};

const emptyOverride: AdminUserOverridePayload = {
  feature_key: "ai_chat_enabled",
  value_type: "boolean",
  value_bool: true,
  value_int: null,
  value_text: null,
  reason: "",
};

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function userLabel(user: AdminUser | AdminUserDetail) {
  return user.email || user.first_name || user.username || `ID ${user.id}`;
}

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
  const [plans, setPlans] = useState<AdminPlan[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [featureForm, setFeatureForm] = useState<AdminPlanFeaturePayload>(emptyFeature);
  const [overrideForm, setOverrideForm] = useState<AdminUserOverridePayload>(emptyOverride);
  const [grantPlanId, setGrantPlanId] = useState<number | "">("");
  const [grantDays, setGrantDays] = useState("");
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
    () => plans.find((plan) => plan.id === selectedPlanId) ?? plans[0] ?? null,
    [plans, selectedPlanId],
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
      const [usersResult, plansResult, subscriptionsResult] = await Promise.allSettled([
        getAdminUsers(currentToken, { q: query || undefined }),
        getAdminPlans(currentToken),
        getAdminSubscriptions(currentToken),
      ]);

      if (usersResult.status === "fulfilled") {
        setUsers(usersResult.value);
      }
      if (plansResult.status === "fulfilled") {
        setPlans(plansResult.value);
        if (!selectedPlanId && plansResult.value.length > 0) {
          setSelectedPlanId(plansResult.value[0].id);
        }
      }
      if (subscriptionsResult.status === "fulfilled") {
        setSubscriptions(subscriptionsResult.value);
      }

      const failed = [usersResult, plansResult, subscriptionsResult].filter((result) => result.status === "rejected");
      if (failed.length > 0) {
        setError("Часть данных админки не загрузилась. Пользователи и тарифы показываются независимо от подписок.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить админку");
    } finally {
      setLoading(false);
    }
  }, [getAccessToken, navigate, query, selectedPlanId, validateSession]);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

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
      setError(err instanceof Error ? err.message : "Не удалось выполнить действие");
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
      if (selectedPlan) {
        await updateAdminPlan(token, selectedPlan.id, planForm);
      } else {
        await createAdminPlan(token, planForm);
      }
    });
  };

  const editPlan = (plan: AdminPlan) => {
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
            </div>
            <div className="grid grid-cols-3 gap-2 rounded-2xl bg-green-50 p-1 text-sm font-semibold text-slate-700">
              {([
                ["users", "Пользователи", UsersRound],
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
                  placeholder="Поиск: email, username, Telegram ID"
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
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-[760px] w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2">ID</th>
                      <th className="px-3 py-2">Имя/email</th>
                      <th className="px-3 py-2">Telegram ID</th>
                      <th className="px-3 py-2">Роль</th>
                      <th className="px-3 py-2">Статус</th>
                      <th className="px-3 py-2">Подписка</th>
                      <th className="px-3 py-2">Создан</th>
                      <th className="px-3 py-2">Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((adminUser) => (
                      <tr key={adminUser.id} className="border-t border-slate-100">
                        <td className="px-3 py-3 font-medium text-slate-900">{adminUser.id}</td>
                        <td className="px-3 py-3">
                          <button type="button" onClick={() => selectUser(adminUser)} className="text-left font-semibold text-green-700">
                            {userLabel(adminUser)}
                          </button>
                          <p className="text-xs text-slate-500">{adminUser.username || "—"}</p>
                        </td>
                        <td className="px-3 py-3">{adminUser.telegram_id || "—"}</td>
                        <td className="px-3 py-3">{adminUser.role}</td>
                        <td className="px-3 py-3">{adminUser.status}</td>
                        <td className="px-3 py-3">{adminUser.subscription_status}</td>
                        <td className="px-3 py-3">{formatDate(adminUser.created_at)}</td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              disabled={saving}
                              onClick={() =>
                                void runAction(async () => {
                                  if (!token) return;
                                  await updateAdminUser(token, adminUser.id, { role: adminUser.role === "admin" ? "user" : "admin" });
                                })
                              }
                              className="rounded-full border border-green-200 px-3 py-1 text-xs font-semibold text-green-700 hover:bg-green-50"
                            >
                              {adminUser.role === "admin" ? "Сделать user" : "Сделать admin"}
                            </button>
                            <button
                              type="button"
                              disabled={saving}
                              onClick={() =>
                                void runAction(async () => {
                                  if (!token) return;
                                  await updateAdminUser(token, adminUser.id, { status: adminUser.status === "blocked" ? "active" : "blocked" });
                                })
                              }
                              className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                            >
                              {adminUser.status === "blocked" ? "Разблокировать" : "Заблокировать"}
                            </button>
                          </div>
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
                    <Info label="Telegram" value={selectedUser.telegram_id || "—"} />
                    <Info label="Подписка" value={selectedUser.subscription_status} />
                    <Info label="Создан" value={formatDate(selectedUser.created_at)} />
                    <Info label="Активна до" value={formatDate(selectedUser.active_subscription_ends_at)} />
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

        {tab === "plans" ? (
          <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {plans.map((plan) => (
                <button
                  key={plan.id}
                  type="button"
                  onClick={() => editPlan(plan)}
                  className="rounded-3xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-green-200 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-green-700">{plan.code}</p>
                      <h2 className="mt-1 text-xl font-bold text-slate-950">{plan.name}</h2>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${plan.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                      {plan.is_active ? "active" : "off"}
                    </span>
                  </div>
                  <p className="mt-3 text-2xl font-bold text-slate-950">
                    {plan.price_amount} {plan.currency}
                  </p>
                  <p className="text-sm text-slate-500">{plan.period_days} дней · features: {plan.features.length}</p>
                </button>
              ))}
            </div>

            <aside className="space-y-4 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-xl font-bold text-slate-950">{selectedPlan ? "Редактировать тариф" : "Новый тариф"}</h2>
                <button type="button" onClick={resetPlanForm} className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600">
                  Новый
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
        onChange={(event) => setValue({ feature_key: event.target.value } as Partial<T>)}
        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
      >
        {FEATURE_PRESETS.map((key) => (
          <option key={key} value={key}>
            {key}
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
