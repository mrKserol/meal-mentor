import axios from "axios";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { NutritionTarget, ProfileUpdatePayload } from "../types/auth";

import { useAuth } from "../hooks/useAuth";

interface FormState {
  email: string;
  password: string;
  sex: "male" | "female" | "";
  birth_date: string;
  height_cm: string;
  weight_kg: string;
  goal: "lose_weight" | "maintain_weight" | "gain_weight" | "";
  activity_level: "1.2" | "1.375" | "1.55" | "1.725" | "1.9" | "";
  target_weight_kg: string;
}

const initialState: FormState = {
  email: "",
  password: "",
  sex: "",
  birth_date: "",
  height_cm: "",
  weight_kg: "",
  goal: "",
  activity_level: "",
  target_weight_kg: "",
};

export function ProfileOnboardingPage() {
  const navigate = useNavigate();
  const { updateProfile } = useAuth();
  const [form, setForm] = useState<FormState>(initialState);
  const [calculatedTarget, setCalculatedTarget] = useState<NutritionTarget | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const payload: ProfileUpdatePayload = {};
      if (form.email) payload.email = form.email;
      if (form.password) payload.password = form.password;
      if (form.sex) payload.sex = form.sex;
      if (form.birth_date) payload.birth_date = form.birth_date;
      if (form.height_cm) payload.height_cm = Number(form.height_cm);
      if (form.weight_kg) payload.weight_kg = Number(form.weight_kg);
      if (form.goal) payload.goal = form.goal;
      if (form.activity_level) payload.activity_level = form.activity_level;
      if (form.target_weight_kg) payload.target_weight_kg = Number(form.target_weight_kg);

      const updated = await updateProfile(payload);

      if (updated.nutrition_target) {
        setCalculatedTarget(updated.nutrition_target);
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.detail ?? "Не удалось сохранить профиль.");
      } else if (requestError instanceof Error) {
        setError(requestError.message);
      } else {
        setError("Не удалось сохранить профиль.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-xl bg-white rounded-xl border border-outline-variant/40 shadow-[0_10px_30px_rgba(0,0,0,0.08)] p-8">
        <h1 className="text-h2 font-h2 text-on-surface mb-2">Заполните профиль питания</h1>
        <p className="text-body-md text-on-surface-variant mb-6">
          Это поможет вести дневник питания точнее. Можно пропустить и пользоваться тарифом Free.
        </p>

        {calculatedTarget ? (
          <div className="space-y-4 rounded-lg border border-primary-container/50 bg-primary-container/10 p-6">
            <p className="text-body-md font-semibold text-on-surface">Рекомендованная цель рассчитана</p>
            <ul className="space-y-1 text-body-md text-on-surface">
              <li>
                Калории:{" "}
                <span className="font-semibold">
                  {calculatedTarget.target_calories} kcal
                </span>
              </li>
              <li>
                Белки:{" "}
                <span className="font-semibold">
                  {calculatedTarget.target_protein_g} g
                </span>
              </li>
              <li>
                Жиры:{" "}
                <span className="font-semibold">{calculatedTarget.target_fat_g} g</span>
              </li>
              <li>
                Углеводы:{" "}
                <span className="font-semibold">
                  {calculatedTarget.target_carbs_g} g
                </span>
              </li>
            </ul>
            <button
              type="button"
              onClick={() => navigate("/dashboard", { replace: true })}
              className="w-full bg-primary-container text-on-primary rounded-lg py-3 font-semibold"
            >
              Перейти в Dashboard
            </button>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-3">
            <input
              className="w-full border border-outline-variant rounded-lg p-3"
              placeholder="Email (опционально)"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
            />
            <input
              className="w-full border border-outline-variant rounded-lg p-3"
              placeholder="Новый пароль (опционально)"
              type="password"
              value={form.password}
              onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
            />

            <select
              className="w-full border border-outline-variant rounded-lg p-3"
              value={form.sex}
              onChange={(e) =>
                setForm((p) => ({ ...p, sex: e.target.value as FormState["sex"] }))
              }
            >
              <option value="">sex (опционально)</option>
              <option value="male">male</option>
              <option value="female">female</option>
            </select>

            <div className="space-y-1">
              <label htmlFor="birth_date" className="block text-sm text-on-surface-variant">
                Дата рождения
              </label>
              <input
                id="birth_date"
                className="w-full border border-outline-variant rounded-lg p-3"
                type="date"
                value={form.birth_date}
                onChange={(e) => setForm((p) => ({ ...p, birth_date: e.target.value }))}
              />
            </div>
            <input
              className="w-full border border-outline-variant rounded-lg p-3"
              type="number"
              placeholder="Рост (height_cm)"
              value={form.height_cm}
              onChange={(e) => setForm((p) => ({ ...p, height_cm: e.target.value }))}
            />
            <input
              className="w-full border border-outline-variant rounded-lg p-3"
              type="number"
              step="0.1"
              placeholder="Вес (weight_kg)"
              value={form.weight_kg}
              onChange={(e) => setForm((p) => ({ ...p, weight_kg: e.target.value }))}
            />

            <select
              className="w-full border border-outline-variant rounded-lg p-3"
              value={form.goal}
              onChange={(e) =>
                setForm((p) => ({ ...p, goal: e.target.value as FormState["goal"] }))
              }
            >
              <option value="">Цель (опционально)</option>
              <option value="lose_weight">Сброс веса</option>
              <option value="maintain_weight">Удержание веса</option>
              <option value="gain_weight">Набор веса</option>
            </select>

            <select
              className="w-full border border-outline-variant rounded-lg p-3"
              value={form.activity_level}
              onChange={(e) =>
                setForm((p) => ({
                  ...p,
                  activity_level: e.target.value as FormState["activity_level"],
                }))
              }
            >
              <option value="">Активность (опционально)</option>
              <option value="1.2">Сидячий образ жизни, без спорта</option>
              <option value="1.375">Лёгкая активность (тренировки 1–3 раза в неделю)</option>
              <option value="1.55">Средняя активность (интенсивные тренировки 3–5 раз в неделю)</option>
              <option value="1.725">Высокая активность (ежедневные нагрузки)</option>
              <option value="1.9">
                Экстремальная активность (тяжёлый физический труд, профессиональный спорт)
              </option>
            </select>

            <input
              className="w-full border border-outline-variant rounded-lg p-3"
              type="number"
              step="0.1"
              placeholder="Желаемый вес"
              value={form.target_weight_kg}
              onChange={(e) =>
                setForm((p) => ({ ...p, target_weight_kg: e.target.value }))
              }
            />

            {error ? <p className="text-label-sm text-error">{error}</p> : null}

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 bg-primary-container text-on-primary rounded-lg py-3 font-semibold disabled:opacity-60"
              >
                {isSubmitting ? "Сохранение..." : "Сохранить профиль"}
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard", { replace: true })}
                className="flex-1 bg-surface-container border border-outline-variant rounded-lg py-3 font-semibold text-on-surface"
              >
                Пропустить
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
