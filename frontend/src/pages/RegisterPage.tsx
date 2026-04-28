import axios from "axios";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerRequest } from "../api/authApi";

interface RegisterFormState {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
  terms: boolean;
}

const initialForm: RegisterFormState = {
  full_name: "",
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

    if (!form.full_name || !form.email || !form.password || !form.confirm_password) {
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
      await registerRequest({
        full_name: form.full_name,
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
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="full_name">
                Полное имя
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                  person
                </span>
                <input
                  id="full_name"
                  value={form.full_name}
                  onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))}
                  className="w-full pl-10 pr-4 py-3 bg-surface border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container focus:border-primary border-solid transition-all outline-none text-on-surface"
                  placeholder="Иван Иванов"
                  type="text"
                />
              </div>
            </div>

            <div className="space-y-xs">
              <label className="font-label-sm text-label-sm text-on-surface-variant ml-1" htmlFor="email">
                Электронная почта
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                  mail
                </span>
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
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                  lock
                </span>
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
              disabled={isSubmitting}
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
    </div>
  );
}
