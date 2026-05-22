import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import {
  getCuratorUserDiary,
  getCuratorUserMealsForDay,
  getCuratorUserNutritionTarget,
  getCuratorUserWeightMeasurements,
} from "../api/curatorApi";
import { DiaryStatsCard } from "../components/diary/DiaryStatsCard";
import { MealHistoryDaySection } from "../components/diary/MealHistoryDaySection";
import { WeightHistoryCard } from "../components/diary/WeightHistoryCard";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";
import type { DiarySnapshot, WeightMeasurementPeriod, WeightMeasurementPoint } from "../types/diary";
import type { NutritionTarget } from "../types/auth";

export function CuratorUserDiaryPage() {
  const { userId: userIdParam } = useParams();
  const selectedUserId = Number(userIdParam);
  const navigate = useNavigate();
  const { user, validateSession, logout, getAccessToken } = useAuth();

  const [snapshot, setSnapshot] = useState<DiarySnapshot | null>(null);
  const [nutritionTarget, setNutritionTarget] = useState<NutritionTarget | null>(null);
  const [diaryPhase, setDiaryPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [diaryError, setDiaryError] = useState<string | null>(null);
  const [weightPeriod, setWeightPeriod] = useState<WeightMeasurementPeriod>("3m");
  const [weightMeasurements, setWeightMeasurements] = useState<WeightMeasurementPoint[]>([]);
  const [weightPhase, setWeightPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [weightError, setWeightError] = useState<string | null>(null);

  const loadDiary = useCallback(async () => {
    if (!Number.isFinite(selectedUserId) || selectedUserId <= 0) {
      setDiaryError("Некорректный ID пользователя");
      setDiaryPhase("error");
      return;
    }
    setDiaryPhase("loading");
    setDiaryError(null);
    try {
      const ok = await validateSession();
      const token = getAccessToken();
      if (!ok || !token) {
        navigate("/login", { replace: true });
        return;
      }
      const [snap, ntEnv] = await Promise.all([
        getCuratorUserDiary(token, selectedUserId),
        getCuratorUserNutritionTarget(token, selectedUserId),
      ]);
      setSnapshot(snap);
      setNutritionTarget(ntEnv.nutrition_target);
      setDiaryPhase("ready");
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 403) {
        setDiaryError("Нет доступа к этому пользователю.");
      } else if (axios.isAxiosError(e) && e.response?.status === 404) {
        setDiaryError("Пользователь не найден.");
      } else {
        setDiaryError(
          axios.isAxiosError(e) && e.response?.data?.detail != null
            ? String(e.response.data.detail)
            : e instanceof Error
              ? e.message
              : "Не удалось загрузить дневник",
        );
      }
      setDiaryPhase("error");
    }
  }, [getAccessToken, navigate, selectedUserId, validateSession]);

  const loadWeightMeasurements = useCallback(async () => {
    if (!Number.isFinite(selectedUserId) || selectedUserId <= 0) return;
    setWeightPhase("loading");
    setWeightError(null);
    try {
      const token = getAccessToken();
      if (!token) return;
      const res = await getCuratorUserWeightMeasurements(token, selectedUserId, weightPeriod);
      setWeightMeasurements(res.items);
      setWeightPhase("ready");
    } catch (e) {
      setWeightError(e instanceof Error ? e.message : "Не удалось загрузить взвешивания");
      setWeightPhase("error");
    }
  }, [getAccessToken, selectedUserId, weightPeriod]);

  useEffect(() => {
    if (user) void loadDiary();
  }, [user?.id, loadDiary]);

  useEffect(() => {
    if (user && diaryPhase === "ready") void loadWeightMeasurements();
  }, [user?.id, diaryPhase, loadWeightMeasurements]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const avatarFallback =
    user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";
  const token = getAccessToken() ?? "";
  const weightKg = snapshot?.weight.weight_kg ?? null;

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-500">Загрузка…</p>
      </div>
    );
  }

  if (diaryPhase === "error" && diaryError) {
    return (
      <AppShell activeNav="home" avatarFallback={avatarFallback} onLogout={handleLogout} showMobileFab={false}>
        <div className="mx-auto max-w-lg p-8 text-center">
          <p className="font-semibold text-slate-900">{diaryError}</p>
          <button
            type="button"
            onClick={() => navigate("/curator")}
            className="mt-4 rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white"
          >
            Назад к списку
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell activeNav="home" avatarFallback={avatarFallback} onLogout={handleLogout} showMobileFab={false}>
      <div className="mx-auto w-full max-w-full overflow-x-hidden p-4 pb-8 lg:max-w-7xl lg:p-8">
        <div className="mb-4 flex justify-end">
          <button
            type="button"
            onClick={() => navigate("/curator")}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Назад
          </button>
        </div>

        <div className="min-w-0 space-y-6">
          {diaryPhase === "loading" && !snapshot ? (
            <p className="text-center text-slate-500">Загружаем данные дневника…</p>
          ) : null}

          <DiaryStatsCard snapshot={snapshot} />

          {token ? (
            <MealHistoryDaySection
              accessToken={token}
              nutritionTarget={nutritionTarget}
              readonly
              getMealsForDay={(t, dateYmd) => getCuratorUserMealsForDay(t, selectedUserId, dateYmd)}
              getNutritionTargetForDay={(t, dateYmd) => getCuratorUserNutritionTarget(t, selectedUserId, dateYmd)}
            />
          ) : null}

          <WeightHistoryCard
            weightKg={weightKg}
            items={weightMeasurements}
            phase={weightPhase}
            error={weightError}
            period={weightPeriod}
            onPeriodChange={setWeightPeriod}
            readonly
          />
        </div>
      </div>
    </AppShell>
  );
}
