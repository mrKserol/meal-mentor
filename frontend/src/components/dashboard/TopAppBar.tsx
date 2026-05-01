import { Bell, HelpCircle, User } from "lucide-react";

interface TopAppBarProps {
  title?: string;
  /** Initial letter or short label for avatar */
  avatarFallback: string;
}

export function TopAppBar({ title = "Meal Mentor", avatarFallback }: TopAppBarProps) {
  const letter = avatarFallback.trim().slice(0, 1).toUpperCase() || "?";

  return (
    <header className="fixed left-0 right-0 top-0 z-50 flex w-full items-center justify-between border-b border-outline-variant/60 bg-white/90 px-4 py-3 shadow-sm backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="truncate font-h3 text-h3 tracking-tight text-primary">{title}</h1>
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <button
          type="button"
          className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
          aria-label="Уведомления (скоро)"
          disabled
        >
          <Bell className="h-5 w-5 opacity-60" aria-hidden />
        </button>
        <button
          type="button"
          className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
          aria-label="Справка (скоро)"
          disabled
        >
          <HelpCircle className="h-5 w-5 opacity-60" aria-hidden />
        </button>
        <div
          className="ml-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-primary-container bg-primary-container/20 font-label-sm font-bold uppercase text-primary"
          title="Профиль"
        >
          {letter === "?" ? <User className="h-4 w-4" aria-hidden /> : letter}
        </div>
      </div>
    </header>
  );
}
