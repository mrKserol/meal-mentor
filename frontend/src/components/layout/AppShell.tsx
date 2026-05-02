import { Plus } from "lucide-react";
import type { ReactNode } from "react";

import type { AppNavItem } from "./appNav";
import { defaultNewMealHandler } from "./appNav";
import { AppMobileBottomNav } from "./AppMobileBottomNav";
import { AppSideNav } from "./AppSideNav";
import { AppTopBar } from "./AppTopBar";

interface AppShellProps {
  activeNav: AppNavItem;
  avatarFallback: string;
  onLogout: () => void | Promise<void>;
  onNewMeal?: () => void;
  /** Show floating + on small screens (above bottom nav) */
  showMobileFab?: boolean;
  children: ReactNode;
}

export function AppShell({
  activeNav,
  avatarFallback,
  onLogout,
  onNewMeal,
  showMobileFab = true,
  children,
}: AppShellProps) {
  const meal = onNewMeal ?? defaultNewMealHandler;

  return (
    <div className="min-h-screen bg-slate-50 pb-24 text-slate-900 antialiased lg:pb-8">
      <AppTopBar avatarFallback={avatarFallback} />
      <div className="flex min-h-screen">
        <AppSideNav activeItem={activeNav} onLogout={onLogout} onNewMeal={meal} />
        <div className="flex min-h-screen flex-1 flex-col pt-14 lg:ml-64">
          <main className="flex-1">{children}</main>
        </div>
      </div>

      {showMobileFab ? (
        <button
          type="button"
          onClick={meal}
          className="fixed bottom-24 right-4 z-[45] flex h-14 w-14 items-center justify-center rounded-full bg-green-600 text-white shadow-lg transition hover:bg-green-700 active:scale-95 lg:hidden"
          aria-label="Записать прием пищи"
        >
          <Plus className="h-7 w-7" aria-hidden strokeWidth={2.5} />
        </button>
      ) : null}

      <AppMobileBottomNav activeItem={activeNav} />
    </div>
  );
}
