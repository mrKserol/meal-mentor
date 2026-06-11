import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Info, X } from "lucide-react";

import { getMyNutritionTarget } from "../api/authApi";
import { addMyWeightMeasurement, getMyDiary, getMyWeightMeasurements } from "../api/diaryApi";
import { DiaryStatsCard } from "../components/diary/DiaryStatsCard";
import { MealHistoryDaySection } from "../components/diary/MealHistoryDaySection";
import { WeightHistoryCard } from "../components/diary/WeightHistoryCard";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";
import type { DiarySnapshot, WeightMeasurementPeriod, WeightMeasurementPoint } from "../types/diary";
import type { NutritionTarget } from "../types/auth";

const MEAL_MENTOR_ACCESS_TOKEN_KEY = "meal_mentor_access_token";

export function DiaryPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, validateSession, logout, getAccessToken } = useAuth();
  const [snapshot, setSnapshot] = useState<DiarySnapshot | null>(null);
  const [nutritionTarget, setNutritionTarget] = useState<NutritionTarget | null>(null);
  const [diaryPhase, setDiaryPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [diaryError, setDiaryError] = useState<string | null>(null);
  const [weightPeriod, setWeightPeriod] = useState<WeightMeasurementPeriod>("3m");
  const [weightMeasurements, setWeightMeasurements] = useState<WeightMeasurementPoint[]>([]);
  const [weightPhase, setWeightPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [weightError, setWeightError] = useState<string | null>(null);
  const [weightModalOpen, setWeightModalOpen] = useState(false);
  const [newWeightKg, setNewWeightKg] = useState("");
  const [newWeightNotes, setNewWeightNotes] = useState("");
  const [weightSaving, setWeightSaving] = useState(false);
  const [weightSaveError, setWeightSaveError] = useState<string | null>(null);
  const [mealHistoryRefresh, setMealHistoryRefresh] = useState(0);

  const loadDiary = useCallback(async () => {
    setDiaryPhase("loading");
    setDiaryError(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        navigate("/login", { replace: true });
        return;
      }
      const token = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const [snap, ntEnv] = await Promise.all([getMyDiary(token), getMyNutritionTarget(token)]);
      setSnapshot(snap);
      setNutritionTarget(ntEnv.nutrition_target);
      setDiaryPhase("ready");
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 401) {
        navigate("/login", { replace: true });
        return;
      }
      const message =
        axios.isAxiosError(e) && e.response?.data?.detail != null
          ? String(e.response.data.detail)
          : e instanceof Error
            ? e.message
            : "Не удалось загрузить дневник";
      setDiaryError(message);
      setDiaryPhase("error");
    }
  }, [getAccessToken, navigate, validateSession]);

  const handleMealSaved = useCallback(() => {
    void loadDiary();
    setMealHistoryRefresh((n) => n + 1);
  }, [loadDiary]);

  const loadWeightMeasurements = useCallback(async () => {
    setWeightPhase("loading");
    setWeightError(null);
    try {
      const token = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const res = await getMyWeightMeasurements(token, weightPeriod);
      setWeightMeasurements(res.items);
      setWeightPhase("ready");
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 401) {
        navigate("/login", { replace: true });
        return;
      }
      const message =
        axios.isAxiosError(e) && e.response?.data?.detail != null
          ? String(e.response.data.detail)
          : e instanceof Error
            ? e.message
            : "Не удалось загрузить взвешивания";
      setWeightError(message);
      setWeightPhase("error");
    }
  }, [getAccessToken, navigate, weightPeriod]);

  useEffect(() => {
    void validateSession();
  }, [validateSession]);

  useEffect(() => {
    if (!user) return;
    void loadDiary();
  }, [user?.id, loadDiary]);

  useEffect(() => {
    if (!user) return;
    void loadWeightMeasurements();
  }, [user?.id, loadWeightMeasurements]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";

  const webDiaryToken = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY) ?? "";
  const requestedMealIdRaw = searchParams.get("mealId");
  const requestedMealId = requestedMealIdRaw ? Number(requestedMealIdRaw) : null;

  const weightKg = snapshot?.weight.weight_kg ?? user?.weight_kg ?? null;

  const closeWeightModal = useCallback(() => {
    if (weightSaving) return;
    setWeightModalOpen(false);
    setWeightSaveError(null);
  }, [weightSaving]);

  const handleSaveWeight = useCallback(async () => {
    const weight = Number(newWeightKg.replace(",", "."));
    if (!Number.isFinite(weight) || weight <= 0) {
      setWeightSaveError("Введите корректный вес.");
      return;
    }
    const token = getAccessToken() ?? localStorage.getItem(MEAL_MENTOR_ACCESS_TOKEN_KEY);
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    setWeightSaving(true);
    setWeightSaveError(null);
    try {
      await addMyWeightMeasurement(token, {
        weight_kg: weight,
        ...(newWeightNotes.trim() ? { notes: newWeightNotes.trim() } : {}),
      });
      setWeightModalOpen(false);
      setNewWeightKg("");
      setNewWeightNotes("");
      await Promise.all([loadDiary(), loadWeightMeasurements()]);
    } catch (e) {
      const message =
        axios.isAxiosError(e) && e.response?.data?.detail != null
          ? String(e.response.data.detail)
          : e instanceof Error
            ? e.message
            : "Не удалось сохранить взвешивание";
      setWeightSaveError(message);
    } finally {
      setWeightSaving(false);
    }
  }, [
    getAccessToken,
    loadDiary,
    loadWeightMeasurements,
    navigate,
    newWeightKg,
    newWeightNotes,
  ]);

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <p className="text-base text-slate-500">Загрузка дневника...</p>
      </div>
    );
  }

  if (diaryPhase === "error" && diaryError) {
    return (
      <AppShell activeNav="diary" avatarFallback={avatarFallback} onLogout={handleLogout} onMealSaved={handleMealSaved}>
        <div className="mx-auto flex max-w-lg flex-col items-center gap-4 p-8 text-center">
          <p className="text-lg font-semibold text-slate-900">Не удалось загрузить данные</p>
          <p className="text-slate-600">{diaryError}</p>
          <button
            type="button"
            onClick={() => void loadDiary()}
            className="rounded-lg bg-green-600 px-6 py-3 font-semibold text-white hover:bg-green-700"
          >
            Попробовать снова
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      activeNav="diary"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      onMealSaved={handleMealSaved}
    >
      {({ openAddMealForDate }) => (
        <div className="mx-auto w-full max-w-full overflow-x-hidden p-4 pb-8 lg:max-w-7xl lg:p-8">
          <div className="min-w-0 space-y-6">
            {diaryPhase === "loading" && !snapshot ? (
              <p className="text-center text-slate-500">Загружаем данные дневника…</p>
            ) : null}

          <section className="rounded-xl border border-green-100 bg-green-50 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white">
                <Info className="h-5 w-5 text-green-600" aria-hidden />
              </div>
              <div>
                <p className="text-sm font-bold text-green-950">Совет ИИ</p>
                <p className="mt-1 text-sm text-slate-600">Пейте больше воды сегодня!</p>
              </div>
            </div>
          </section>

          <DiaryStatsCard snapshot={snapshot} />

          {webDiaryToken ? (
            <MealHistoryDaySection
              accessToken={webDiaryToken}
              nutritionTarget={nutritionTarget}
              refreshToken={mealHistoryRefresh}
              initialOpenMealId={Number.isFinite(requestedMealId) ? requestedMealId : null}
              onMealsChanged={handleMealSaved}
              onAddMealForDay={openAddMealForDate}
            />
          ) : null}

          <WeightHistoryCard
            weightKg={weightKg}
            items={weightMeasurements}
            phase={weightPhase}
            error={weightError}
            period={weightPeriod}
            onPeriodChange={setWeightPeriod}
            onAddWeight={() => {
              setNewWeightKg(weightKg != null ? weightKg.toFixed(1) : "");
              setWeightSaveError(null);
              setWeightModalOpen(true);
            }}
          />

          {weightModalOpen ? (
            <div
              className="fixed inset-0 z-[100] flex items-end justify-center bg-black/45 p-0 sm:items-center sm:p-4"
              role="dialog"
              aria-modal="true"
              aria-labelledby="weight-modal-title"
              onMouseDown={(e) => {
                if (e.target === e.currentTarget) closeWeightModal();
              }}
            >
              <div className="w-full max-w-md rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 id="weight-modal-title" className="text-xl font-semibold text-slate-900">
                    Добавить взвешивание
                  </h2>
                  <button
                    type="button"
                    onClick={closeWeightModal}
                    className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                    aria-label="Закрыть"
                  >
                    <X className="h-5 w-5" aria-hidden />
                  </button>
                </div>

                <div className="space-y-4">
                  <label className="flex flex-col gap-1">
                    <span className="text-sm font-medium text-slate-600">Вес, кг</span>
                    <input
                      type="number"
                      min={1}
                      step="0.1"
                      inputMode="decimal"
                      value={newWeightKg}
                      onChange={(e) => setNewWeightKg(e.target.value)}
                      className="h-12 w-full rounded-lg border border-slate-200 bg-slate-50 px-4 text-base outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                    />
                  </label>

                  <label className="flex flex-col gap-1">
                    <span className="text-sm font-medium text-slate-600">Заметка</span>
                    <textarea
                      value={newWeightNotes}
                      onChange={(e) => setNewWeightNotes(e.target.value)}
                      rows={3}
                      className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-base outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                    />
                  </label>

                  {weightSaveError ? <p className="text-sm text-red-600">{weightSaveError}</p> : null}

                  <button
                    type="button"
                    onClick={() => void handleSaveWeight()}
                    disabled={weightSaving}
                    className="flex w-full items-center justify-center rounded-lg bg-green-600 px-4 py-3 font-semibold text-white transition hover:bg-green-700 disabled:opacity-60"
                  >
                    {weightSaving ? "Сохраняем..." : "Сохранить"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
          </div>
        </div>
      )}
    </AppShell>
  );
}
