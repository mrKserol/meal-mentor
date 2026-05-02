import { BarChart3, CalendarDays, LayoutDashboard, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { AppNavItem } from "./appNav";

interface AppMobileBottomNavProps {
  activeItem: AppNavItem;
  onCompositionClick?: () => void;
}

const itemBase = "flex flex-col items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium";
const itemActive = `${itemBase} font-bold text-green-600`;
const itemIdle = `${itemBase} text-slate-400`;
const itemDisabled = `${itemBase} cursor-not-allowed text-slate-400 opacity-50`;

export function AppMobileBottomNav({ activeItem, onCompositionClick }: AppMobileBottomNavProps) {
  const navigate = useNavigate();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-slate-200 bg-white px-2 py-2 pb-[max(env(safe-area-inset-bottom),0.75rem)] pt-2 lg:hidden">
      <button
        type="button"
        onClick={() => navigate("/dashboard")}
        className={activeItem === "home" ? itemActive : itemIdle}
      >
        <LayoutDashboard className="h-6 w-6" aria-hidden strokeWidth={activeItem === "home" ? 2.5 : 2} />
        Главная
      </button>
      <button type="button" disabled title="Скоро" className={itemDisabled}>
        <CalendarDays className="h-6 w-6" aria-hidden />
        Дневник
      </button>
      <button
        type="button"
        onClick={onCompositionClick}
        disabled={!onCompositionClick}
        title={onCompositionClick ? "Проверить состав по этикетке" : undefined}
        className={onCompositionClick ? itemIdle : itemDisabled}
      >
        <BarChart3 className="h-6 w-6" aria-hidden />
        Состав
      </button>
      <button
        type="button"
        onClick={() => navigate("/onboarding/profile")}
        className={activeItem === "profile" ? itemActive : itemIdle}
      >
        <UserRound className="h-6 w-6" aria-hidden strokeWidth={activeItem === "profile" ? 2.5 : 2} />
        Профиль
      </button>
    </nav>
  );
}
