export interface AuthRegisterPayload {
  full_name: string;
  email: string;
  password: string;
}

export interface AuthLoginPayload {
  email: string;
  password: string;
}

export interface AuthTokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_in: number;
}

export interface MeUser {
  id: number;
  email: string | null;
  username: string | null;
  telegram_id: number | null;
  subscription_status: string;
  created_at: string;
}
