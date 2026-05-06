import { Bell, ChevronDown, HelpCircle, LogOut, User, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

interface AppTopBarProps {
  title?: string;
  avatarFallback: string;
  onLogout: () => void | Promise<void>;
}

export function AppTopBar({ title = "Meal Mentor", avatarFallback, onLogout }: AppTopBarProps) {
  const navigate = useNavigate();
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const letter = avatarFallback.trim().slice(0, 1).toUpperCase() || "?";

  useEffect(() => {
    if (!profileMenuOpen) return;

    const handleMouseDown = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setProfileMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [profileMenuOpen]);

  return (
    <header className="fixed left-0 right-0 top-0 z-50 flex w-full items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 shadow-sm backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <img
          src="/icons/smallicon.png"
          alt=""
          className="h-8 w-8 shrink-0 object-contain"
          width={32}
          height={32}
          aria-hidden
        />
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

        <div ref={menuRef} className="relative ml-1">
          <button
            type="button"
            onClick={() => setProfileMenuOpen((prev) => !prev)}
            className="flex items-center gap-1 rounded-full border border-green-200 bg-green-50 py-1 pl-1 pr-2 text-sm font-bold uppercase text-green-700 transition hover:bg-green-100"
            title="Профиль"
            aria-label="Открыть меню профиля"
            aria-expanded={profileMenuOpen}
            aria-haspopup="menu"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-green-200 bg-white">
              {letter === "?" ? <User className="h-4 w-4" aria-hidden /> : letter}
            </span>
            <ChevronDown className="h-4 w-4" aria-hidden />
          </button>

          {profileMenuOpen ? (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-48 overflow-hidden rounded-xl border border-slate-200 bg-white py-2 shadow-lg shadow-slate-900/10"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setProfileMenuOpen(false);
                  navigate("/onboarding/profile");
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                <UserRound className="h-4 w-4 text-slate-500" aria-hidden />
                Мой профиль
              </button>

              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setProfileMenuOpen(false);
                  void onLogout();
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm font-medium text-red-600 transition hover:bg-red-50"
              >
                <LogOut className="h-4 w-4" aria-hidden />
                Выйти
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
