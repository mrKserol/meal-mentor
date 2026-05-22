export type NutrientField = {
  key: string;
  label: string;
  unit: string;
};

export type AdditiveAnalyzeResponse = {
  status: string;
  serving_label: string | null;
  serving_size_g: number | null;
  nutrients: Record<string, number>;
  ignored: Array<{ label: string; amount: string | null; reason?: string }>;
  confidence: number | null;
  error?: string | null;
};

export type AdditiveItem = {
  id: number;
  additive_name: string;
  photo_large: string | null;
  photo_thumb: string | null;
  photo_large_url: string | null;
  photo_thumb_url: string | null;
  serving_label: string | null;
  serving_size_g: number | null;
  nutrients: Record<string, number>;
  created_at: string;
  updated_at: string | null;
};

export type AdditiveListResponse = {
  items: AdditiveItem[];
};

export type AdditiveCreatePayload = {
  additive_name: string;
  serving_label?: string | null;
  serving_size_g?: number | null;
  image_base64?: string | null;
  nutrients?: Record<string, number>;
};

export type AdditiveUpdatePayload = {
  additive_name?: string;
  serving_label?: string | null;
  serving_size_g?: number | null;
  image_base64?: string | null;
  nutrients?: Record<string, number>;
};

export type AdditiveIntakeItem = {
  id: number;
  additive_id: number | null;
  additive_name_snapshot: string;
  servings_count: number;
  intake_datetime: string;
  time_local: string;
  nutrients: Record<string, number>;
  water_g: number | null;
};

export type AdditiveIntakeListResponse = {
  date: string;
  items: AdditiveIntakeItem[];
};

export type AdditiveIntakeCreatePayload = {
  additive_id: number;
  servings_count: number;
  intake_local_date?: string;
};

export type WaterIntakeCreatePayload = {
  amount_ml?: number;
  intake_local_date?: string;
};
