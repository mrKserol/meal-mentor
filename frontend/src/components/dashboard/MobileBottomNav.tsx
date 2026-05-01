import { Calendar, ChefHat, LayoutDashboard, User } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function MobileBottomNav() {
  const navigate = useNavigate();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-outline-variant bg-white px-4 py-2 pb-[max(env(safe-area-inset-bottom),0.75rem)] pt-3 lg:hidden">
      <button
        type="button"
        onClick={() => navigate("/dashboard")}
        className="flex flex-col items-center gap-1 rounded-lg px-3 py-1 text-xs font-bold text-primary"
      >
        <LayoutDashboard className="h-6 w-6" aria-hidden strokeWidth={2.25} />
        Главная
      </button>
      <button
        type="button"
        disabled
        title="Скоро"
        className="flex flex-col items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-on-surface-variant opacity-50"
      >
        <Calendar className="h-6 w-6" aria-hidden />
        Дневник
      </button>
      <button
        type="button"
        disabled
        title="Скоро"
        className="flex flex-col items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-on-surface-variant opacity-50"
      >
        <ChefHat className="h-6 w-6" aria-hidden />
        Состав
      </button>
      <button
        type="button"
        disabled
        title="Скоро"
        className="flex flex-col items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-on-surface-variant opacity-50"
      >
        <User className="h-6 w-6" aria-hidden />
        Профиль
      </button>
    </nav>
  );
}
