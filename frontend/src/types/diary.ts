export interface DiaryRecentMeal {
  id: number;
  title: string;
  meal_type: string | null;
  meal_type_label: string;
  time_local: string;
  calories: number;
  recorded_at: string;
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

export interface DiarySnapshot {
  recent_meals: DiaryRecentMeal[];
  week: DiaryWeekBlock;
  today: DiaryTodayTotals;
  weight: DiaryWeightCard;
}
