import axios from "axios";
import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

interface LoginFormState {
  email: string;
  password: string;
}

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<LoginFormState>({ email: "", password: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!form.email || !form.password) {
      setError("Введите email и пароль.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email: form.email, password: form.password });
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.detail ?? "Не удалось войти.");
      } else {
        setError("Произошла неизвестная ошибка.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="font-body-md text-on-surface min-h-screen flex items-center justify-center p-margin relative bg-surface">
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none -z-10 overflow-hidden opacity-40">
        <div className="absolute top-[-10%] right-[-5%] w-[400px] h-[400px] bg-primary-container/10 rounded-full blur-3xl" />
        <div className="absolute bottom-[-5%] left-[-5%] w-[300px] h-[300px] bg-tertiary-container/10 rounded-full blur-3xl" />
        <div className="absolute top-20 left-20 text-primary-container/20 rotate-12">
          <span className="material-symbols-outlined text-[64px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            eco
          </span>
        </div>
        <div className="absolute bottom-40 right-20 text-secondary-container/30 -rotate-12">
          <span className="material-symbols-outlined text-[48px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            nutrition
          </span>
        </div>
        <div className="absolute top-1/2 left-10 text-primary/10">
          <span className="material-symbols-outlined text-[56px]">monitoring</span>
        </div>
      </div>

      <main className="w-full max-w-[420px] z-10">
        <div className="flex flex-col items-center mb-xl">
          <div className="w-20 h-20 mb-md bg-white rounded-xl shadow-[0_4px_12px_rgba(46,204,113,0.1)] flex items-center justify-center overflow-hidden border border-outline-variant/30">
            <img
              alt="Robot Mentor Logo"
              className="w-14 h-14 object-contain"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuB8WOAfIdFkP6JxE4-yLUCwNZUClMHp-ubhR60BO0RGHc8p1_eKq12LLwtcLdcdauu-cmAUKG76zKxoUh4KQUMxAwBVSGirpO84klfMnw0TeSQR1z_Zjb1UlNOSlCqT5XqdXJeq1oX-4Y0OL4qd5tnLTBzX4-oQkXbOioHSjEGbQZoRNpLkccddEF1kDEvf0_Deu-d8aSmkNV4aVqXsdx00D8BzdSIJcCwYgYrENsXrL0zkIHB8LWEQBRIR15rA9zI60TrH69WZgogn"
            />
          </div>
          <h1 className="font-h1 text-h1 text-on-surface mb-xs">Вход в Meal Mentor</h1>
          <p className="font-body-md text-on-surface-variant text-center px-lg">
            Ваш персональный ИИ-диетолог для здорового образа жизни
          </p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/50 p-lg shadow-[0_8px_32px_rgba(0,0,0,0.05)]">
          <form className="space-y-lg" onSubmit={onSubmit}>
            <div className="space-y-sm">
              <label className="block font-label-sm text-label-sm text-on-surface-variant" htmlFor="email">
                Электронная почта
              </label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
                  mail
                </span>
                <input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                  placeholder="example@mail.com"
                  className="w-full bg-surface py-3 pl-11 pr-4 rounded-lg border border-outline-variant focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none transition-all font-body-md text-on-surface placeholder:text-outline/60"
                />
              </div>
            </div>

            <div className="space-y-sm">
              <div className="flex justify-between items-center">
                <label className="block font-label-sm text-label-sm text-on-surface-variant" htmlFor="password">
                  Пароль
                </label>
                <a className="font-label-sm text-label-sm text-primary hover:underline transition-all" href="#">
                  Забыли пароль?
                </a>
              </div>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
                  lock
                </span>
                <input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                  placeholder="••••••••"
                  className="w-full bg-surface py-3 pl-11 pr-4 rounded-lg border border-outline-variant focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none transition-all font-body-md text-on-surface placeholder:text-outline/60"
                />
              </div>
            </div>

            {error ? <p className="text-label-sm text-error">{error}</p> : null}

            <button
              className="w-full bg-primary-container text-on-primary py-4 rounded-lg font-h3 text-h3 hover:opacity-90 active:scale-[0.98] transition-all shadow-[0_4px_14px_rgba(46,204,113,0.3)] disabled:opacity-60"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Вход..." : "Войти"}
            </button>
          </form>

          <div className="relative my-xl">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-outline-variant/30" />
            </div>
            <div className="relative flex justify-center text-label-sm">
              <span className="bg-surface-container-lowest px-4 text-on-surface-variant font-label-sm">или через</span>
            </div>
          </div>

          <div className="relative bg-secondary-container/30 p-md rounded-xl border border-secondary-container/50 flex gap-md items-start mb-md">
            <div className="shrink-0 text-primary-container">
              <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
                smart_toy
              </span>
            </div>
            <p className="font-body-md text-label-sm text-on-secondary-container italic">
              «Привет! Давай продолжим путь к твоему идеальному рациону сегодня.»
            </p>
          </div>
        </div>

        <div className="mt-lg text-center">
          <p className="font-body-md text-on-surface-variant">
            Нет аккаунта?{" "}
            <Link className="text-primary font-semibold hover:underline ml-xs transition-all" to="/register">
              Зарегистрироваться
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
