import type { AdminPlanFeaturePayload, AdminUserOverridePayload } from "../api/adminApi";

export const FEATURE_PRESETS = [
  "nutrition_diary_enabled",
  "advanced_nutrients_enabled",
  "food_photo_recognition_enabled",
  "label_analysis_enabled",
  "ai_chat_enabled",
  "allergens_enabled",
  "daily_ai_requests_limit",
  "daily_ai_chat_messages_limit",
  "daily_photo_recognition_limit",
  "monthly_photo_recognition_limit",
  "monthly_label_analysis_limit",
] as const;

export const FEATURE_LABELS: Record<string, string> = {
  nutrition_diary_enabled: "Дневник питания",
  advanced_nutrients_enabled: "Расширенные нутриенты",
  food_photo_recognition_enabled: "Распознавание еды по фото",
  label_analysis_enabled: "Анализ этикеток",
  ai_chat_enabled: "ИИ-чат",
  allergens_enabled: "Учет аллергенов",
  daily_ai_requests_limit: "Дневной лимит ИИ-запросов",
  daily_ai_chat_messages_limit: "Дневной лимит сообщений в ИИ-чате",
  daily_photo_recognition_limit: "Дневной лимит распознаваний фото",
  monthly_photo_recognition_limit: "Месячный лимит распознаваний фото",
  monthly_label_analysis_limit: "Месячный лимит анализов этикеток",
};

export const BOOLEAN_FEATURES = new Set([
  "nutrition_diary_enabled",
  "advanced_nutrients_enabled",
  "food_photo_recognition_enabled",
  "label_analysis_enabled",
  "ai_chat_enabled",
  "allergens_enabled",
]);

export const LIMIT_FEATURES = new Set([
  "daily_ai_requests_limit",
  "daily_ai_chat_messages_limit",
  "daily_photo_recognition_limit",
  "monthly_photo_recognition_limit",
  "monthly_label_analysis_limit",
]);

export function getDefaultFeaturePayload(featureKey: string): AdminPlanFeaturePayload {
  if (BOOLEAN_FEATURES.has(featureKey)) {
    return {
      feature_key: featureKey,
      feature_name: FEATURE_LABELS[featureKey] ?? featureKey,
      value_type: "boolean",
      value_bool: true,
      value_int: null,
      value_text: null,
    };
  }

  return {
    feature_key: featureKey,
    feature_name: FEATURE_LABELS[featureKey] ?? featureKey,
    value_type: "limit",
    value_bool: null,
    value_int: 0,
    value_text: null,
  };
}

export const emptyFeature: AdminPlanFeaturePayload = getDefaultFeaturePayload("nutrition_diary_enabled");

export const emptyOverride: AdminUserOverridePayload = {
  feature_key: "nutrition_diary_enabled",
  value_type: "boolean",
  value_bool: true,
  value_int: null,
  value_text: null,
  reason: "",
};

export function featureOptionLabel(key: string): string {
  const label = FEATURE_LABELS[key] ?? key;
  return `${label} — ${key}`;
}
