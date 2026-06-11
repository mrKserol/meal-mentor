import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "../components/AdminRoute";
import { CuratorRoute } from "../components/CuratorRoute";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AdminPage } from "../pages/AdminPage";
import { CuratorPage } from "../pages/CuratorPage";
import { CuratorUserDiaryPage } from "../pages/CuratorUserDiaryPage";
import { DashboardPage } from "../pages/DashboardPage";
import { DiaryPage } from "../pages/DiaryPage";
import { DisclaimerPage } from "../pages/DisclaimerPage";
import { LoginPage } from "../pages/LoginPage";
import { ProfileOnboardingPage } from "../pages/ProfileOnboardingPage";
import { RegisterPage } from "../pages/RegisterPage";
import { TelegramCallbackPage } from "../pages/TelegramCallbackPage";
import { YandexCallbackPage } from "../pages/YandexCallbackPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/telegram/callback" element={<TelegramCallbackPage />} />
      <Route path="/auth/yandex/callback" element={<YandexCallbackPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/onboarding/profile" element={<ProfileOnboardingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/diary" element={<DiaryPage />} />
        <Route path="/disclaimer" element={<DisclaimerPage />} />
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminPage />} />
        </Route>
        <Route element={<CuratorRoute />}>
          <Route path="/curator" element={<CuratorPage />} />
          <Route path="/curator/users/:userId" element={<CuratorUserDiaryPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
