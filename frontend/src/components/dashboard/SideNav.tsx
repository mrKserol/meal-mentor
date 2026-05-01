import { BarChart3, Calendar, HelpCircle, LayoutDashboard, LogOut, Plus, Settings } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

interface SideNavProps {
  onLogout: () => Promise<void>;
}

export function SideNav({ onLogout }: SideNavProps) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const dashActive = pathname === "/dashboard";

  return (
    <aside className="fixed left-0 top-14 z-40 hidden h-[calc(100vh-3.5rem)] w-64 flex-col border-r border-outline-variant/60 bg-surface-container-low p-4 lg:flex">
      <div className="mb-6 px-2">
        <p className="font-h3 text-h3 text-on-surface">Meal Mentor</p>
        <p className="text-body-md text-on-surface-variant">AI-помощник по питанию</p>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className={
            dashActive
              ? "flex items-center gap-3 rounded-lg bg-white px-4 py-3 text-left text-sm font-medium text-primary shadow-sm transition-colors"
              : "flex items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium text-on-surface transition-colors hover:bg-primary-container/15 hover:text-primary"
          }
        >
          <LayoutDashboard className="h-5 w-5 shrink-0" aria-hidden />
          <span>Главная</span>
        </button>
        <button
          type="button"
          disabled
          title="Скоро"
          className="flex cursor-not-allowed items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium text-on-surface-variant opacity-60"
        >
          <Calendar className="h-5 w-5 shrink-0" aria-hidden />
          <span>Дневник</span>
        </button>
        <button
          type="button"
          disabled
          title="Скоро"
          className="flex cursor-not-allowed items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium text-on-surface-variant opacity-60"
        >
          <BarChart3 className="h-5 w-5 shrink-0" aria-hidden />
          <span>Состав</span>
        </button>
        <button
          type="button"
          onClick={() => navigate("/onboarding/profile")}
          className="flex items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium text-on-surface transition-colors hover:bg-primary-container/15 hover:text-primary"
        >
          <Settings className="h-5 w-5 shrink-0" aria-hidden />
          <span>Профиль</span>
        </button>
      </nav>

      <div className="mt-auto space-y-2 border-t border-outline-variant/60 pt-4">
        <button
          type="button"
          disabled
          title="Скоро"
          className="flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-primary-container px-4 py-3 font-bold text-on-primary opacity-75"
        >
          <Plus className="h-5 w-5" aria-hidden />
          Записать приём пищи
        </button>
        <button
          type="button"
          disabled
          title="Скоро"
          className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium text-on-surface-variant opacity-70"
        >
          <HelpCircle className="h-5 w-5 shrink-0" aria-hidden />
          <span>Помощь</span>
        </button>
        <button
          type="button"
          onClick={() => void onLogout()}
          className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium text-on-surface transition-colors hover:bg-error-container/40 hover:text-error"
        >
          <LogOut className="h-5 w-5 shrink-0" aria-hidden />
          <span>Выйти</span>
        </button>
      </div>
    </aside>
  );
}
