const GOALS: Record<string, string> = {
  lose_weight: "Снижение веса",
  maintain_weight: "Поддержание веса",
  gain_weight: "Набор массы",
};

export type UserGoal = "lose_weight" | "maintain_weight" | "gain_weight";

/** Same rules as backend `derive_goal_from_weights`. */
export function deriveGoalFromWeights(
  weightKg?: number | null,
  targetWeightKg?: number | null,
): UserGoal | null {
  if (weightKg == null || targetWeightKg == null || Number.isNaN(Number(weightKg)) || Number.isNaN(Number(targetWeightKg))) {
    return null;
  }
  const current = Number(weightKg);
  const target = Number(targetWeightKg);
  if (current > target) return "lose_weight";
  if (current < target) return "gain_weight";
  return "maintain_weight";
}

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

/** Full years from ISO birth date (YYYY-MM-DD). */
export function ageYearsFromBirthDate(birthDate?: string | null): number | null {
  if (!birthDate) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birthDate.trim());
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(d)) return null;
  const today = new Date();
  let years = today.getFullYear() - y;
  const monthDay = (today.getMonth() + 1) * 100 + today.getDate();
  const birthMonthDay = mo * 100 + d;
  if (monthDay < birthMonthDay) years -= 1;
  return years >= 0 ? years : null;
}

export function formatWeightKgRu(value?: number | null): string {
  if (value == null || Number.isNaN(Number(value))) {
    return "—";
  }
  const n = Number(value);
  const text = Number.isInteger(n) ? String(n) : n.toFixed(1).replace(".", ",");
  return `${text} кг`;
}

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
