export interface WebMealDayItemLine {
  id: number;
  item_name: string | null;
  name_translated?: string | null;
  name_language?: string | null;
  display_name?: string | null;
  ingredient_state?: string | null;
  estimated_weight_g: number | null;
  calories: number | null;
  protein_g: number | null;
  fat_g: number | null;
  carbs_g: number | null;
  fiber_g: number | null;
}

export interface WebMealDayRow {
  id: number;
  prediction: string | null;
  prediction_translated?: string | null;
  prediction_language?: string | null;
  display_prediction?: string | null;
  user_text: string | null;
  time_local: string;
  meal_type: string | null;
  meal_type_label: string;
  composition: string;
  calories: number;
  protein_g?: number;
  fat_g?: number;
  carbs_g?: number;
  fiber_g?: number;
  sugar_g?: number;
  sodium_mg?: number;
  saturated_fat_g?: number;
  water_g?: number;
  meal_photo_thumb: string | null;
  meal_photo_large: string | null;
  meal_photo_thumb_url: string | null;
  meal_photo_large_url: string | null;
  items: WebMealDayItemLine[];
}

export interface WebMealsDayResponse {
  date: string;
  items: WebMealDayRow[];
}
