import axios from "axios";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { register } from "../api/authApi";
import { InstallPwaHint } from "../components/InstallPwaHint";

interface RegisterFormState {
  telegram_username: string;
  first_name: string;
  sex: "male" | "female" | "other";
  birth_date: string;
  height_cm: string;
  weight_kg: string;
  activity_level: "1.2" | "1.375" | "1.55" | "1.725" | "1.9";
  target_weight_kg: string;
  email: string;
  password: string;
  confirm_password: string;
  terms: boolean;
}

const initialForm: RegisterFormState = {
  telegram_username: "",
  first_name: "",
  sex: "male",
  birth_date: "",
  height_cm: "",
  weight_kg: "",
  activity_level: "1.375",
  target_weight_kg: "",
  email: "",
  password: "",
  confirm_password: "",
  terms: false,
};

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<RegisterFormState>(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (
      !form.telegram_username ||
      !form.first_name ||
      !form.birth_date ||
      !form.height_cm ||
      !form.weight_kg ||
      !form.target_weight_kg ||
      !form.email ||
      !form.password ||
      !form.confirm_password
    ) {
      setError("Пожалуйста, заполните все обязательные поля.");
      return;
    }
    if (form.password !== form.confirm_password) {
      setError("Пароли не совпадают.");
      return;
    }
    if (!form.terms) {
      setError("Необходимо согласиться с условиями обслуживания.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        telegram_username: form.telegram_username,
        first_name: form.first_name,
        sex: form.sex,
        birth_date: form.birth_date,
        height_cm: Number(form.height_cm),
        weight_kg: Number(form.weight_kg),
        activity_level: form.activity_level,
        target_weight_kg: Number(form.target_weight_kg),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        email: form.email,
        password: form.password,
      });
      navigate("/login", { replace: true });
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.detail ?? "Не удалось зарегистрироваться.");
      } else {
        setError("Произошла неизвестная ошибка.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-surface font-body-md text-on-surface antialiased min-h-screen flex items-center justify-center relative overflow-x-hidden">
      <div className="absolute top-[-10%] left-[-5%] w-[40%] h-[40%] bg-primary-container/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-tertiary-container/5 rounded-full blur-3xl pointer-events-none" />

      <main className="w-full max-w-md px-margin relative z-10 py-xl">
        <div className="bg-surface-container-lowest border border-surface-variant rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.04)] p-lg flex flex-col items-center">
          <div className="mb-lg text-center">
            <img
              alt="Meal Mentor Logo"
              className="w-20 h-20 mx-auto mb-sm"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDQw5qJ9vuI8c46jsvi5DOrqgCZbxJuGm0odtiDW6HbLXmJlWNoTt_6PJbiQyPuiRNZ3MsMQOIkq0cGIOKx8Wm4BmrYqQeITLjv5A5Ytuj6eSbXfHFgKhPptyfa8C8whpMkMxTp_DGj7_2LnR_OMZpD78MaqblO1c0ez_iJ0yES4o5TakUKcNA-axGgY4-bS8VTjgYsr0TZ-flabyIsIDtRvftNVa320ZDOcdDmg9FPKxebSQ3Zxsy3QWFqad4tCHKJkltWNk7vObXO"
            />
            <h1 className="font-h1 text-h1 text-on-surface mb-xs">Регистрация в Meal Mentor</h1>
            <p className="font-body-md text-on-surface-variant">Начните путь к здоровому питанию сегодня</p>
          </div>

          <form className="w-full space-y-md" onSubmit={onSubmit}>
            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="telegram_username">
                Telegram username
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                  person
                </span>
                <input
                  id="telegram_username"
                  value={form.telegram_username}
                  onChange={(e) => setForm((prev) => ({ ...prev, telegram_username: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary border-solid transition-all outline-none text-on-surface"
                  placeholder="my_username"
                  type="text"
                />
              </div>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="first_name">
                Имя
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                  badge
                </span>
                <input
                  id="first_name"
                  value={form.first_name}
                  onChange={(e) => setForm((prev) => ({ ...prev, first_name: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary border-solid transition-all outline-none text-on-surface"
                  placeholder="Иван"
                  type="text"
                />
              </div>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="sex">
                Пол
              </label>
              <select
                id="sex"
                value={form.sex}
                onChange={(e) => setForm((prev) => ({ ...prev, sex: e.target.value as RegisterFormState["sex"] }))}
                className="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary transition-all outline-none text-on-surface"
              >
                <option value="male">male</option>
                <option value="female">female</option>
                <option value="other">other</option>
              </select>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="birth_date">
                Дата рождения
              </label>
              <input
                id="birth_date"
                value={form.birth_date}
                onChange={(e) => setForm((prev) => ({ ...prev, birth_date: e.target.value }))}
                className="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary transition-all outline-none text-on-surface"
                type="date"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-sm">
              <div className="relative">
                <input
                  id="height_cm"
                  value={form.height_cm}
                  onChange={(e) => setForm((prev) => ({ ...prev, height_cm: e.target.value }))}
                  className="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary transition-all outline-none text-on-surface"
                  placeholder="Рост (см)"
                  type="number"
                />
              </div>
              <div className="relative">
                <input
                  id="weight_kg"
                  value={form.weight_kg}
                  onChange={(e) => setForm((prev) => ({ ...prev, weight_kg: e.target.value }))}
                  className="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary transition-all outline-none text-on-surface"
                  placeholder="Вес (кг)"
                  type="number"
                  step="0.1"
                />
              </div>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="activity_level">
                Активность
              </label>
              <select
                id="activity_level"
                value={form.activity_level}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, activity_level: e.target.value as RegisterFormState["activity_level"] }))
                }
                className="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary transition-all outline-none text-on-surface"
              >
                <option value="1.2">Сидячий образ жизни, без спорта</option>
                <option value="1.375">Лёгкая активность (тренировки 1–3 раза в неделю)</option>
                <option value="1.55">Средняя активность (интенсивные тренировки 3–5 раз в неделю)</option>
                <option value="1.725">Высокая активность (ежедневные нагрузки)</option>
                <option value="1.9">
                  Экстремальная активность (тяжёлый физический труд, профессиональный спорт)
                </option>
              </select>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="target_weight_kg">
                Целевой вес (кг)
              </label>
              <input
                id="target_weight_kg"
                value={form.target_weight_kg}
                onChange={(e) => setForm((prev) => ({ ...prev, target_weight_kg: e.target.value }))}
                className="w-full px-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary transition-all outline-none text-on-surface"
                type="number"
                step="0.1"
              />
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="email">
                Электронная почта
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">mail</span>
                <input
                  id="email"
                  value={form.email}
                  onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary border-solid transition-all outline-none text-on-surface"
                  placeholder="example@mail.com"
                  type="email"
                />
              </div>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="password">
                Пароль
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">lock</span>
                <input
                  id="password"
                  value={form.password}
                  onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary border-solid transition-all outline-none text-on-surface"
                  placeholder="••••••••"
                  type="password"
                />
              </div>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="confirm_password">
                Подтвердите пароль
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                  lock_reset
                </span>
                <input
                  id="confirm_password"
                  value={form.confirm_password}
                  onChange={(e) => setForm((prev) => ({ ...prev, confirm_password: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary border-solid transition-all outline-none text-on-surface"
                  placeholder="••••••••"
                  type="password"
                />
              </div>
            </div>

            <div className="flex items-start gap-sm pt-xs">
              <div className="flex items-center h-5">
                <input
                  id="terms"
                  checked={form.terms}
                  onChange={(e) => setForm((prev) => ({ ...prev, terms: e.target.checked }))}
                  className="w-5 h-5 rounded border-outline-variant text-primary-container focus:ring-primary-container cursor-pointer bg-surface"
                  type="checkbox"
                />
              </div>
              <label className="font-label-sm text-label-sm text-on-surface-variant cursor-pointer leading-tight" htmlFor="terms">
                Я согласен с <a className="text-primary hover:underline" href="#">Условиями обслуживания</a> и{" "}
                <a className="text-primary hover:underline" href="#">Политикой конфиденциальности</a>
              </label>
            </div>

            {error ? <p className="text-label-sm text-error mt-xs">{error}</p> : null}

            <button
              className="w-full bg-primary-container hover:bg-on-primary-container text-on-primary-container font-h3 text-h3 py-4 rounded-lg shadow-md transition-all active:scale-[0.98] mt-md disabled:opacity-60"
              type="submit"
              disabled={!form.terms || isSubmitting}
            >
              {isSubmitting ? "Создание..." : "Создать аккаунт"}
            </button>
          </form>

          <div className="w-full flex items-center gap-sm my-lg">
            <div className="flex-1 h-[1px] bg-outline-variant" />
            <span className="font-label-sm text-label-sm text-outline">ИЛИ</span>
            <div className="flex-1 h-[1px] bg-outline-variant" />
          </div>

          <p className="font-body-md text-on-surface-variant">
            Уже есть аккаунт?{" "}
            <Link className="text-primary font-semibold hover:underline decoration-2 underline-offset-4" to="/login">
              Войти
            </Link>
          </p>
        </div>

        <footer className="mt-lg text-center space-y-sm">
          <div className="flex justify-center items-center gap-xs text-on-secondary-container">
            <span className="material-symbols-outlined text-[18px]">help_outline</span>
            <span className="font-label-sm text-label-sm">Нужна помощь с регистрацией?</span>
          </div>
          <p className="font-label-sm text-label-sm text-outline px-lg">
            Meal Mentor использует ИИ для персонализации вашего плана питания. Ваши данные надежно защищены.
          </p>
        </footer>
      </main>

      <InstallPwaHint />
    </div>
  );
}
