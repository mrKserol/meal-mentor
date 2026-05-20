import { authClient } from "./authApi";

const authHeaders = (token: string) => ({ Authorization: `Bearer ${token}` });

export interface AdminPlanFeature {
  id: number;
  plan_id: number;
  feature_key: string;
  feature_name: string;
  value_type: "boolean" | "limit" | "text";
  value_bool: boolean | null;
  value_int: number | null;
  value_text: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminPlan {
  id: number;
  code: string;
  name: string;
  description: string | null;
  price_amount: number;
  currency: string;
  period_days: number;
  is_active: boolean;
  sort_order: number;
  created_at: string | null;
  updated_at: string | null;
  features: AdminPlanFeature[];
}

export interface AdminUser {
  id: number;
  email: string | null;
  provider: string | null;
  telegram_id: number | null;
  username: string | null;
  first_name: string | null;
  role: "user" | "admin";
  status: "active" | "blocked";
  subscription_status: string;
  created_at: string;
  updated_at: string | null;
  active_subscription_ends_at: string | null;
}

export interface AdminSubscription {
  id: number;
  user_id: number;
  user_email: string | null;
  user_name: string | null;
  plan: string;
  plan_id: number | null;
  plan_name: string | null;
  status: string;
  provider: string | null;
  payment_status: string | null;
  started_at: string | null;
  ends_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  activated_by_admin_id: number | null;
}

export interface AdminUserFeatureOverride {
  id: number;
  user_id: number;
  feature_key: string;
  value_type: "boolean" | "limit" | "text";
  value_bool: boolean | null;
  value_int: number | null;
  value_text: string | null;
  reason: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AdminUserDetail extends AdminUser {
  active_subscription: AdminSubscription | null;
  subscriptions: AdminSubscription[];
  feature_overrides: AdminUserFeatureOverride[];
}

export type AdminPlanPayload = Omit<AdminPlan, "id" | "created_at" | "updated_at" | "features">;
export type AdminPlanUpdatePayload = Partial<AdminPlanPayload>;

export interface AdminPlanFeaturePayload {
  feature_key: string;
  feature_name: string;
  value_type: "boolean" | "limit" | "text";
  value_bool?: boolean | null;
  value_int?: number | null;
  value_text?: string | null;
}

export interface AdminUserUpdatePayload {
  role?: "user" | "admin";
  status?: "active" | "blocked";
  subscription_status?: string;
}

export interface AdminGrantSubscriptionPayload {
  plan_id: number;
  days?: number;
}

export interface AdminUserOverridePayload {
  feature_key: string;
  value_type: "boolean" | "limit" | "text";
  value_bool?: boolean | null;
  value_int?: number | null;
  value_text?: string | null;
  reason?: string | null;
}

export const getAdminUsers = async (token: string, params?: Record<string, string | number | undefined>) => {
  const response = await authClient.get<AdminUser[]>("/admin/users", { params, headers: authHeaders(token) });
  return response.data;
};

export const getAdminUser = async (token: string, userId: number) => {
  const response = await authClient.get<AdminUserDetail>(`/admin/users/${userId}`, { headers: authHeaders(token) });
  return response.data;
};

export const updateAdminUser = async (token: string, userId: number, payload: AdminUserUpdatePayload) => {
  const response = await authClient.patch<AdminUser>(`/admin/users/${userId}`, payload, { headers: authHeaders(token) });
  return response.data;
};

export const deleteAdminUser = async (token: string, userId: number): Promise<void> => {
  await authClient.delete(`/admin/users/${userId}`, { headers: authHeaders(token) });
};

export const getAdminPlans = async (token: string) => {
  const response = await authClient.get<AdminPlan[]>("/admin/plans", { headers: authHeaders(token) });
  return response.data;
};

export const createAdminPlan = async (token: string, payload: AdminPlanPayload) => {
  const response = await authClient.post<AdminPlan>("/admin/plans", payload, { headers: authHeaders(token) });
  return response.data;
};

export const updateAdminPlan = async (token: string, planId: number, payload: AdminPlanUpdatePayload) => {
  const response = await authClient.patch<AdminPlan>(`/admin/plans/${planId}`, payload, { headers: authHeaders(token) });
  return response.data;
};

export const deleteAdminPlan = async (token: string, planId: number) => {
  const response = await authClient.delete(`/admin/plans/${planId}`, { headers: authHeaders(token) });
  return response.data;
};

export const upsertPlanFeature = async (
  token: string,
  planId: number,
  featureKey: string,
  payload: AdminPlanFeaturePayload,
) => {
  const response = await authClient.put<AdminPlanFeature>(`/admin/plans/${planId}/features/${featureKey}`, payload, {
    headers: authHeaders(token),
  });
  return response.data;
};

export const deletePlanFeature = async (token: string, planId: number, featureId: number) => {
  await authClient.delete(`/admin/plans/${planId}/features/${featureId}`, { headers: authHeaders(token) });
};

export const grantSubscription = async (token: string, userId: number, payload: AdminGrantSubscriptionPayload) => {
  const response = await authClient.post<AdminSubscription>(`/admin/users/${userId}/grant-subscription`, payload, {
    headers: authHeaders(token),
  });
  return response.data;
};

export const cancelSubscription = async (token: string, subscriptionId: number) => {
  const response = await authClient.post<AdminSubscription>(`/admin/subscriptions/${subscriptionId}/cancel`, null, {
    headers: authHeaders(token),
  });
  return response.data;
};

export const getAdminSubscriptions = async (token: string, params?: Record<string, string | number | undefined>) => {
  const response = await authClient.get<AdminSubscription[]>("/admin/subscriptions", { params, headers: authHeaders(token) });
  return response.data;
};

export const getUserFeatureOverrides = async (token: string, userId: number) => {
  const response = await authClient.get<AdminUserFeatureOverride[]>(`/admin/users/${userId}/feature-overrides`, {
    headers: authHeaders(token),
  });
  return response.data;
};

export const upsertUserFeatureOverride = async (
  token: string,
  userId: number,
  featureKey: string,
  payload: AdminUserOverridePayload,
) => {
  const response = await authClient.put<AdminUserFeatureOverride>(
    `/admin/users/${userId}/feature-overrides/${featureKey}`,
    payload,
    { headers: authHeaders(token) },
  );
  return response.data;
};

export const deleteUserFeatureOverride = async (token: string, userId: number, featureKey: string) => {
  await authClient.delete(`/admin/users/${userId}/feature-overrides/${featureKey}`, { headers: authHeaders(token) });
};
