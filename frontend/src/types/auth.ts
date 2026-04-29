export interface RegisterPayload {
  telegram_username: string;
  first_name: string;
  sex: "male" | "female" | "other";
  birth_date: string;
  height_cm: number;
  weight_kg: number;
  goal: "lose_weight" | "maintain_weight" | "gain_weight";
  activity_level: "low" | "moderate" | "high";
  target_weight_kg: number;
  timezone: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TelegramCallbackPayload {
  code: string;
  state: string;
  code_verifier: string;
  redirect_uri: string;
  timezone: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_in: number;
  user?: User;
  is_new_user?: boolean;
  profile_completed?: boolean;
}

export interface User {
  id: number;
  email: string | null;
  username: string | null;
  first_name: string | null;
  sex: string | null;
  birth_date: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  goal: string | null;
  activity_level: string | null;
  target_weight_kg: number | null;
  timezone: string | null;
  telegram_id: number | null;
  subscription_status: string;
  created_at: string;
  updated_at: string | null;
  profile_completed: boolean;
}

export interface ProfileUpdatePayload {
  email?: string;
  password?: string;
  sex?: "male" | "female" | "other";
  birth_date?: string;
  height_cm?: number;
  weight_kg?: number;
  goal?: "lose_weight" | "maintain_weight" | "gain_weight";
  activity_level?: "low" | "moderate" | "high";
  target_weight_kg?: number;
}
