export interface NutritionTarget {
  bmr_kcal: number;
  tdee_kcal: number;
  target_calories: number;
  target_fiber_g: number;
  target_protein_g: number;
  target_fat_g: number;
  target_carbs_g: number;
  formula_name: string;
  goal?: string | null;
  activity_level?: string | null;
  weight_kg?: number | null;
  target_weight_kg?: number | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string | null;
}

export interface MyNutritionTargetEnvelope {
  nutrition_target: NutritionTarget | null;
}

export interface RegisterPayload {
  telegram_username: string;
  first_name: string;
  sex: "male" | "female" | "other";
  birth_date: string;
  height_cm: number;
  weight_kg: number;
  goal: "lose_weight" | "maintain_weight" | "gain_weight";
  activity_level: "1.2" | "1.375" | "1.55" | "1.725" | "1.9";
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

export interface YandexCallbackPayload {
  code: string;
  state: string;
  redirect_uri: string;
  timezone?: string;
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
  role: "user" | "admin";
  status: "active" | "blocked";
  subscription_status: string;
  created_at: string;
  updated_at: string | null;
  profile_completed: boolean;
  nutrition_target?: NutritionTarget | null;
  allergens: string[];
}

export interface ProfileUpdatePayload {
  email?: string;
  password?: string;
  sex?: "male" | "female" | "other";
  birth_date?: string;
  height_cm?: number;
  weight_kg?: number;
  goal?: "lose_weight" | "maintain_weight" | "gain_weight";
  activity_level?:
    | "1.2"
    | "1.375"
    | "1.55"
    | "1.725"
    | "1.9"
    | "low"
    | "moderate"
    | "high"
    | "1"
    | "1.3"
    | "1.5";
  target_weight_kg?: number;
  allergens?: string[];
}
