import { BarChart3, CalendarDays, LayoutDashboard, Plus, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { AppNavItem } from "./appNav";

const navBtnBase =
  "flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium transition-colors";
const navInactive = `${navBtnBase} text-slate-600 hover:bg-green-50 hover:text-green-700`;
const navActive = `${navBtnBase} border border-slate-100 bg-white text-green-600 shadow-sm`;
const navDisabled = `${navBtnBase} cursor-not-allowed text-slate-400 opacity-60`;

interface AppSideNavProps {
  activeItem: AppNavItem;
  onNewMeal?: () => void;
  onCompositionClick?: () => void;
}

export function AppSideNav({ activeItem, onNewMeal, onCompositionClick }: AppSideNavProps) {
  const navigate = useNavigate();
  const meal = onNewMeal ?? (() => {});

  return (
    <aside className="fixed left-0 top-14 z-40 hidden h-[calc(100vh-3.5rem)] w-64 flex-col border-r border-slate-200 bg-slate-50 p-4 lg:flex">
      <div className="mb-6 px-2">
        <p className="text-lg font-black text-slate-900">Meal Mentor</p>
        <p className="text-sm font-medium leading-relaxed text-slate-500">AI Nutrition Guide</p>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className={activeItem === "home" ? navActive : navInactive}
        >
          <LayoutDashboard className="h-5 w-5 shrink-0" aria-hidden />
          <span>Главная</span>
        </button>
        <button
          type="button"
          onClick={() => navigate("/diary")}
          className={activeItem === "diary" ? navActive : navInactive}
        >
          <CalendarDays className="h-5 w-5 shrink-0" aria-hidden />
          <span>Дневник</span>
        </button>
        <button
          type="button"
          onClick={onCompositionClick}
          disabled={!onCompositionClick}
          title={onCompositionClick ? "Проверить состав по этикетке" : undefined}
          className={onCompositionClick ? navInactive : navDisabled}
        >
          <BarChart3 className="h-5 w-5 shrink-0" aria-hidden />
          <span>Состав</span>
        </button>
        <button
          type="button"
          onClick={() => navigate("/onboarding/profile")}
          className={activeItem === "profile" ? navActive : navInactive}
        >
          <UserRound className="h-5 w-5 shrink-0" aria-hidden />
          <span>Профиль</span>
        </button>
      </nav>

      <div className="mt-auto space-y-2 border-t border-slate-200 pt-4">
        <button
          type="button"
          onClick={meal}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-3 font-bold text-white shadow-sm transition hover:bg-green-700 active:scale-[0.98]"
        >
          <Plus className="h-5 w-5 shrink-0" aria-hidden />
          Запись
        </button>
      </div>
    </aside>
  );
}
