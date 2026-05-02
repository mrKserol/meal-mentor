import axios from "axios";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Bean,
  Cherry,
  CircleCheck,
  Citrus,
  Egg,
  Fish,
  Info,
  Milk,
  Nut,
  Plus,
  Save,
  Shrimp,
  Target,
  Trees,
  TriangleAlert,
  UserRound,
  Wheat,
} from "lucide-react";

import { AppShell } from "../components/layout/AppShell";
import { defaultNewMealHandler } from "../components/layout/appNav";
import { useAuth } from "../hooks/useAuth";
import type { ProfileUpdatePayload, User } from "../types/auth";

type ProfileFormState = {
  sex: string;
  birth_date: string;
  height_cm: string;
  weight_kg: string;
  goal: string;
  activity_level: string;
  target_weight_kg: string;
};

const emptyForm: ProfileFormState = {
  sex: "",
  birth_date: "",
  height_cm: "",
  weight_kg: "",
  goal: "",
  activity_level: "",
  target_weight_kg: "",
};

function userToForm(u: User): ProfileFormState {
  const sexRaw = u.sex ?? "";
  const sexNormalized = sexRaw === "male" || sexRaw === "female" ? sexRaw : "";
  return {
    sex: sexNormalized,
    birth_date: u.birth_date ?? "",
    height_cm: u.height_cm != null ? String(u.height_cm) : "",
    weight_kg: u.weight_kg != null ? String(u.weight_kg) : "",
    goal: u.goal ?? "",
    activity_level: u.activity_level ?? "",
    target_weight_kg: u.target_weight_kg != null ? String(u.target_weight_kg) : "",
  };
}

const ALLERGEN_OPTIONS: { id: string; label: string; Icon: LucideIcon }[] = [
  { id: "dairy", label: "Молочные продукты", Icon: Milk },
  { id: "eggs", label: "Яйца", Icon: Egg },
  { id: "peanuts", label: "Арахис", Icon: Nut },
  { id: "shellfish", label: "Моллюски", Icon: Shrimp },
  { id: "gluten", label: "Глютен", Icon: Wheat },
  { id: "fish", label: "Рыба", Icon: Fish },
  { id: "soy", label: "Соя", Icon: Bean },
  { id: "tree_nuts", label: "Древесные орехи", Icon: Trees },
  { id: "citrus", label: "Цитрусовые", Icon: Citrus },
  { id: "nightshades", label: "Помидоры / пасленовые", Icon: Cherry },
  { id: "other", label: "Другое", Icon: Plus },
];

function buildPayload(form: ProfileFormState): ProfileUpdatePayload {
  const payload: ProfileUpdatePayload = {};
  if (form.sex) payload.sex = form.sex as ProfileUpdatePayload["sex"];
  if (form.birth_date) payload.birth_date = form.birth_date;
  if (form.height_cm) payload.height_cm = Number(form.height_cm);
  if (form.weight_kg) payload.weight_kg = Number(form.weight_kg);
  if (form.goal) payload.goal = form.goal as ProfileUpdatePayload["goal"];
  if (form.activity_level) {
    payload.activity_level = form.activity_level as ProfileUpdatePayload["activity_level"];
  }
  if (form.target_weight_kg) payload.target_weight_kg = Number(form.target_weight_kg);
  return payload;
}

export function ProfileOnboardingPage() {
  const navigate = useNavigate();
  const { user, updateProfile, validateSession, logout } = useAuth();
  const [form, setForm] = useState<ProfileFormState>(emptyForm);
  /** Local only until PATCH /users/me/profile supports allergens. */
  const [selectedAllergens, setSelectedAllergens] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    void validateSession();
  }, [validateSession]);

  useEffect(() => {
    if (!user) return;
    setForm(userToForm(user));
  }, [user]);

  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const toggleAllergen = (id: string) => {
    setSelectedAllergens((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    setIsSaving(true);
    try {
      // TODO: send allergens to profile save API when backend is ready (e.g. allergens: string[])
      await updateProfile(buildPayload(form));
      setSuccess("Профиль обновлен");
      window.setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(String(err.response?.data?.detail ?? "Не удалось сохранить профиль."));
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Не удалось сохранить профиль.");
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  const nutritionTarget = user?.nutrition_target ?? null;

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <p className="text-base text-slate-500">Загрузка профиля...</p>
      </div>
    );
  }

  const inputClass =
    "w-full h-12 rounded-lg border border-slate-200 bg-slate-50 px-4 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100";

  return (
    <AppShell
      activeNav="profile"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      onNewMeal={defaultNewMealHandler}
    >
      <div className="mx-auto max-w-7xl p-4 pb-8 lg:p-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Профиль пользователя</h1>
          <p className="mt-2 text-slate-500">
            Управляйте данными о здоровье и диетическими предпочтениями.
          </p>
        </header>

        {error ? (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {success ? (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            {success}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <section className="space-y-6 lg:col-span-8">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-green-50">
                  <UserRound className="h-6 w-6 text-green-600" aria-hidden />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-slate-900">Личная информация</h2>
                  <p className="text-sm text-slate-500">Эти данные нужны для расчёта калорий и БЖУ.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-slate-600">Пол</span>
                  <select name="sex" value={form.sex} onChange={handleChange} className={inputClass}>
                    <option value="">Не указано</option>
                    <option value="male">Мужской</option>
                    <option value="female">Женский</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-slate-600">Дата рождения</span>
                  <input
                    name="birth_date"
                    type="date"
                    value={form.birth_date}
                    onChange={handleChange}
                    className={inputClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-slate-600">Рост, см</span>
                  <input
                    name="height_cm"
                    type="number"
                    min={1}
                    inputMode="numeric"
                    placeholder="180"
                    value={form.height_cm}
                    onChange={handleChange}
                    className={inputClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-slate-600">Актуальный вес, кг</span>
                  <input
                    name="weight_kg"
                    type="number"
                    min={1}
                    step="0.1"
                    inputMode="decimal"
                    placeholder="75"
                    value={form.weight_kg}
                    onChange={handleChange}
                    className={inputClass}
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-slate-600">Цель</span>
                  <select name="goal" value={form.goal} onChange={handleChange} className={inputClass}>
                    <option value="">Не указано</option>
                    <option value="lose_weight">Снижение веса</option>
                    <option value="maintain_weight">Поддержание веса</option>
                    <option value="gain_weight">Набор массы</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-slate-600">Желаемый вес, кг</span>
                  <input
                    name="target_weight_kg"
                    type="number"
                    min={1}
                    step="0.1"
                    inputMode="decimal"
                    placeholder="70"
                    value={form.target_weight_kg}
                    onChange={handleChange}
                    className={inputClass}
                  />
                </label>

                <label className="flex flex-col gap-1 md:col-span-2">
                  <span className="text-sm font-medium text-slate-600">Уровень активности</span>
                  <select
                    name="activity_level"
                    value={form.activity_level}
                    onChange={handleChange}
                    className={inputClass}
                  >
                    <option value="">Не указано</option>
                    <option value="1.2">Сидячий образ жизни, отсутствие спорта</option>
                    <option value="1.375">Легкая активность — тренировки 1–3 раза в неделю</option>
                    <option value="1.55">Средняя активность — интенсивные тренировки 3–5 раз в неделю</option>
                    <option value="1.725">Высокая активность — ежедневные нагрузки</option>
                    <option value="1.9">
                      Экстремальная активность — физический труд / профессиональный спорт
                    </option>
                  </select>
                </label>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-amber-100">
                  <TriangleAlert className="h-6 w-6 text-amber-700" aria-hidden />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-slate-900">Аллергены</h2>
                  <p className="text-sm text-slate-500">
                    Выберите продукты, которые вам противопоказаны.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {ALLERGEN_OPTIONS.map(({ id, label, Icon }) => {
                  const selected = selectedAllergens.includes(id);
                  return (
                    <label
                      key={id}
                      htmlFor={`allergen-${id}`}
                      className={`group relative flex cursor-pointer flex-col items-center overflow-hidden rounded-xl border p-4 transition-colors ${
                        selected
                          ? "border-green-600 bg-green-50/80 shadow-sm"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      <input
                        id={`allergen-${id}`}
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleAllergen(id)}
                        className="sr-only"
                      />
                      <div
                        className={`mb-2 flex h-12 w-12 items-center justify-center rounded-lg ${
                          selected ? "bg-white shadow-sm" : "bg-slate-50"
                        }`}
                      >
                        <Icon className="h-7 w-7 text-slate-600" aria-hidden />
                      </div>
                      <span className="text-center text-sm font-medium text-slate-800">{label}</span>
                      {selected ? (
                        <CircleCheck
                          className="absolute right-1 top-1 h-5 w-5 text-green-600"
                          aria-hidden
                        />
                      ) : null}
                    </label>
                  );
                })}
              </div>
            </div>
          </section>

          <aside className="space-y-6 lg:col-span-4">
            <div className="rounded-xl bg-green-700 p-6 text-white shadow-lg shadow-green-900/20">
              <div className="mb-4 flex items-center gap-3">
                <Target className="h-6 w-6 shrink-0" aria-hidden />
                <h3 className="text-xl font-semibold">Дневная цель (КБЖУ)</h3>
              </div>

              {nutritionTarget ? (
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between border-b border-white/15 py-2">
                    <span className="text-white/90">Калории</span>
                    <span className="font-bold">{nutritionTarget.target_calories} kcal</span>
                  </div>
                  <div className="flex justify-between border-b border-white/15 py-2">
                    <span className="text-white/90">Белки</span>
                    <span className="font-bold">{nutritionTarget.target_protein_g} g</span>
                  </div>
                  <div className="flex justify-between border-b border-white/15 py-2">
                    <span className="text-white/90">Жиры</span>
                    <span className="font-bold">{nutritionTarget.target_fat_g} g</span>
                  </div>
                  <div className="flex justify-between border-b border-white/15 py-2">
                    <span className="text-white/90">Углеводы</span>
                    <span className="font-bold">{nutritionTarget.target_carbs_g} g</span>
                  </div>
                  <div className="flex justify-between border-b border-white/15 py-2">
                    <span className="text-white/90">BMR</span>
                    <span className="font-bold">{nutritionTarget.bmr_kcal} kcal</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-white/90">TDEE</span>
                    <span className="font-bold">{nutritionTarget.tdee_kcal} kcal</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-sm text-white/95">
                  <p className="font-semibold">Дневная цель пока не рассчитана</p>
                  <p>
                    Заполните пол, дату рождения, рост, вес, цель, желаемый вес и уровень активности.
                  </p>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-50">
                  <Info className="h-5 w-5 text-green-600" aria-hidden />
                </div>
                <div>
                  <h4 className="mb-1 text-lg font-semibold text-slate-900">Совет ментора</h4>
                  <p className="text-sm leading-relaxed text-slate-600">
                    {nutritionTarget
                      ? "На основе ваших данных рассчитана дневная цель по формуле Миффлина-Сан Жеора."
                      : "Заполните профиль, чтобы рассчитать дневную норму калорий и БЖУ."}
                  </p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={isSaving}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 py-3 font-semibold text-white shadow-sm transition hover:bg-green-700 disabled:opacity-60"
            >
              <Save className="h-5 w-5 shrink-0" aria-hidden />
              {isSaving ? "Сохраняем..." : "Сохранить изменения профиля"}
            </button>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
