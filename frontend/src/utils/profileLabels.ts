const GOALS: Record<string, string> = {
  lose_weight: "Снижение веса",
  maintain_weight: "Поддержание веса",
  gain_weight: "Набор массы",
};

/** PAL / TDEE multiplier → short label */
const ACTIVITY_NEW: Record<string, string> = {
  "1.2": "Сидячий образ жизни",
  "1.375": "Легкая активность",
  "1.55": "Средняя активность",
  "1.725": "Высокая активность",
  "1.9": "Экстремальная активность",
};

const ACTIVITY_LEGACY: Record<string, string> = {
  "1": "Минимальная активность",
  "1.0": "Минимальная активность",
  "1.3": "Средняя активность",
  "1.5": "Высокая активность",
  low: "Минимальная активность",
  moderate: "Средняя активность",
  high: "Высокая активность",
};

export function getGoalLabel(goal?: string | null): string {
  if (goal == null || goal === "") {
    return "Не указано";
  }
  return GOALS[goal] ?? goal;
}

export function getActivityLevelLabel(activityLevel?: string | null): string {
  if (activityLevel == null || activityLevel === "") {
    return "Не указано";
  }
  const key = activityLevel.trim();
  if (ACTIVITY_NEW[key]) {
    return ACTIVITY_NEW[key];
  }
  try {
    const n = Number(key.replace(",", "."));
    const rounded = String(n);
    if (ACTIVITY_NEW[rounded]) {
      return ACTIVITY_NEW[rounded];
    }
    for (const [k, label] of Object.entries(ACTIVITY_NEW)) {
      if (Math.abs(Number(k) - n) < 1e-3) {
        return label;
      }
    }
  } catch {
    /* ignore */
  }
  const low = key.toLowerCase();
  return ACTIVITY_LEGACY[low] ?? activityLevel;
}

export function getSubscriptionLabel(status?: string | null): string {
  const s = (status ?? "").trim().toLowerCase();
  if (!s || s === "free") {
    return "Free";
  }
  if (s.includes("premium") || s === "paid" || s === "pro") {
    return "Premium";
  }
  return status ?? "Free";
}

export function subscriptionIsFree(status?: string | null): boolean {
  const s = (status ?? "").trim().toLowerCase();
  return !s || s === "free";
}
