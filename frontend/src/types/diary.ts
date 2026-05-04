export interface DiaryRecentMeal {
  id: number;
  title: string;
  meal_type: string | null;
  meal_type_label: string;
  time_local: string;
  calories: number;
  protein_g?: number;
  fat_g?: number;
  carbs_g?: number;
  fiber_g?: number;
  recorded_at: string;
  prediction?: string | null;
  user_text?: string | null;
  composition?: string;
  meal_photo_large?: string | null;
  meal_photo_thumb?: string | null;
  meal_photo_large_url?: string | null;
  meal_photo_thumb_url?: string | null;
}

export interface DiaryWeekDay {
  date: string;
  weekday_short: string;
  calories: number;
  bar_percent: number;
}

export interface DiaryWeekBlock {
  days: DiaryWeekDay[];
  avg_calories: number;
  avg_protein_g: number;
  avg_fat_g: number;
  avg_carbs_g: number;
  days_with_data: number;
}

export interface DiaryTodayTotals {
  calories: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
}

export interface DiaryWeightCard {
  weight_kg: number | null;
  delta_week_kg: number | null;
}

export interface DiaryPeriodDay {
  date: string;
  label: string;
  calories: number;
  bar_percent: number;
}

export interface DiaryPeriodBlock {
  days: DiaryPeriodDay[];
  avg_calories: number;
  avg_protein_g: number;
  avg_fat_g: number;
  avg_carbs_g: number;
  days_with_data: number;
}

export interface DiarySnapshot {
  today_meals: DiaryRecentMeal[];
  week: DiaryWeekBlock;
  month: DiaryPeriodBlock;
  today: DiaryTodayTotals;
  weight: DiaryWeightCard;
}
