import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function DashboardPage() {
  const navigate = useNavigate();
  const { logout, user, validateSession } = useAuth();

  useEffect(() => {
    const check = async () => {
      const isValid = await validateSession();
      if (!isValid) {
        navigate("/login", { replace: true });
      }
    };
    void check();
  }, [navigate, validateSession]);

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-xl bg-white rounded-xl border border-outline-variant/40 shadow-[0_10px_30px_rgba(0,0,0,0.08)] p-8 text-center space-y-5">
        <h1 className="text-h1 font-h1 text-on-surface">Meal Mentor</h1>
        <p className="text-body-md font-body-md text-on-surface-variant">Авторизация успешно работает</p>
        {user ? (
          <div className="space-y-1">
            <p className="text-label-sm font-label-sm text-outline">
              Вы вошли как: <span className="text-on-surface">{user.first_name ?? user.username ?? "пользователь"}</span>
            </p>
            <p className="text-label-sm font-label-sm text-outline">
              Тариф: <span className="text-on-surface">{user.subscription_status}</span>
            </p>
          </div>
        ) : null}
        {user && !user.profile_completed ? (
          <div className="bg-secondary-container/30 border border-secondary-container/60 rounded-lg p-4">
            <p className="text-sm text-on-secondary-container mb-2">Профиль питания не заполнен</p>
            <button
              type="button"
              onClick={() => navigate("/onboarding/profile")}
              className="text-primary font-semibold hover:underline"
            >
              Заполнить профиль
            </button>
          </div>
        ) : null}
        {user?.nutrition_target ? (
          <div className="text-left bg-surface-container border border-outline-variant/50 rounded-lg p-5 space-y-3">
            <h2 className="text-h3 font-h3 text-on-surface">Ваша дневная цель</h2>
            <ul className="space-y-1 text-body-md text-on-surface-variant">
              <li>
                Калории:{" "}
                <span className="font-semibold text-on-surface">
                  {user.nutrition_target.target_calories} kcal
                </span>
              </li>
              <li>
                Белки:{" "}
                <span className="font-semibold text-on-surface">
                  {user.nutrition_target.target_protein_g} g
                </span>
              </li>
              <li>
                Жиры:{" "}
                <span className="font-semibold text-on-surface">
                  {user.nutrition_target.target_fat_g} g
                </span>
              </li>
              <li>
                Углеводы:{" "}
                <span className="font-semibold text-on-surface">
                  {user.nutrition_target.target_carbs_g} g
                </span>
              </li>
            </ul>
          </div>
        ) : user ? (
          <div className="text-left bg-surface-container border border-outline-variant/50 rounded-lg p-5 space-y-3">
            <h2 className="text-h3 font-h3 text-on-surface">Ваша дневная цель</h2>
            <p className="text-body-md text-on-surface-variant">
              Заполните профиль, чтобы рассчитать дневную цель
            </p>
            <button
              type="button"
              onClick={() => navigate("/onboarding/profile")}
              className="inline-flex items-center justify-center bg-primary-container text-on-primary py-2 px-5 rounded-lg font-semibold"
            >
              Заполнить профиль
            </button>
          </div>
        ) : null}
        <button
          onClick={onLogout}
          className="inline-flex items-center justify-center bg-primary-container hover:opacity-90 text-on-primary py-3 px-8 rounded-lg font-semibold transition"
          type="button"
        >
          Выйти
        </button>
      </div>
    </div>
  );
}
