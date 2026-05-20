import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "../components/AdminRoute";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AdminPage } from "../pages/AdminPage";
import { DashboardPage } from "../pages/DashboardPage";
import { DiaryPage } from "../pages/DiaryPage";
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
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
