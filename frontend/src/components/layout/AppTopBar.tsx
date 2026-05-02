import { Bell, HelpCircle, User } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface AppTopBarProps {
  title?: string;
  avatarFallback: string;
}

export function AppTopBar({ title = "Meal Mentor", avatarFallback }: AppTopBarProps) {
  const navigate = useNavigate();
  const letter = avatarFallback.trim().slice(0, 1).toUpperCase() || "?";

  return (
    <header className="fixed left-0 right-0 top-0 z-50 flex w-full items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 shadow-sm backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="truncate text-lg font-bold tracking-tight text-green-600 sm:text-xl">{title}</h1>
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <button
          type="button"
          className="rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-100"
          aria-label="Уведомления (скоро)"
          disabled
        >
          <Bell className="h-5 w-5 opacity-60" aria-hidden />
        </button>
        <button
          type="button"
          className="rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-100"
          aria-label="Справка (скоро)"
          disabled
        >
          <HelpCircle className="h-5 w-5 opacity-60" aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => navigate("/onboarding/profile")}
          className="ml-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-green-200 bg-green-50 text-sm font-bold uppercase text-green-700 transition hover:bg-green-100"
          title="Профиль"
          aria-label="Открыть профиль"
        >
          {letter === "?" ? <User className="h-4 w-4" aria-hidden /> : letter}
        </button>
      </div>
    </header>
  );
}
