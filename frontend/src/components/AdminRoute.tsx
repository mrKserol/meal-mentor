import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function AdminRoute() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="font-body-md text-slate-600">Проверка доступа...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user?.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-green-700">Meal Mentor</p>
          <h1 className="mt-3 text-2xl font-bold text-slate-950">Нет доступа</h1>
          <p className="mt-2 text-sm text-slate-600">Этот раздел доступен только администраторам.</p>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
