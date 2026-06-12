import { Plus } from "lucide-react";
import { useCallback, useState, type ReactNode } from "react";

import { AddMealOpenProvider } from "../../context/AddMealContext";
import type { AppNavItem } from "./appNav";
import { AddMealModal } from "./AddMealModal";
import { AppMobileBottomNav } from "./AppMobileBottomNav";
import { AppSideNav } from "./AppSideNav";
import { AppTopBar } from "./AppTopBar";
import { CompositionLabelModal } from "./CompositionLabelModal";

export type AppShellActions = {
  openAddMeal: () => void;
  /** Открыть «Добавить приём» с записью на выбранный календарный день (дата + текущее время). */
  openAddMealForDate: (dateYmd: string) => void;
};

type AppShellChildren = ReactNode | ((actions: AppShellActions) => ReactNode);

interface AppShellProps {
  activeNav: AppNavItem;
  avatarFallback: string;
  onLogout: () => void | Promise<void>;
  /** Вызывается после успешного сохранения приёма пищи (обновление дневника и т.п.). */
  onMealSaved?: () => void;
  /** Show floating + on small screens (above bottom nav) */
  showMobileFab?: boolean;
  lockViewport?: boolean;
  children: AppShellChildren;
}

export function AppShell({
  activeNav,
  avatarFallback,
  onLogout,
  onMealSaved,
  showMobileFab = true,
  lockViewport = false,
  children,
}: AppShellProps) {
  const [addMealOpen, setAddMealOpen] = useState(false);
  const [mealLocalDate, setMealLocalDate] = useState<string | null>(null);
  const openAddMeal = useCallback(() => {
    setMealLocalDate(null);
    setAddMealOpen(true);
  }, []);
  const openAddMealForDate = useCallback((dateYmd: string) => {
    setMealLocalDate(dateYmd);
    setAddMealOpen(true);
  }, []);
  const closeAddMeal = useCallback(() => {
    setAddMealOpen(false);
    setMealLocalDate(null);
  }, []);

  const renderChildren = () => {
    if (typeof children === "function") {
      return (children as (actions: AppShellActions) => ReactNode)({ openAddMeal, openAddMealForDate });
    }
    return children;
  };

  const [compositionOpen, setCompositionOpen] = useState(false);
  const openComposition = useCallback(() => setCompositionOpen(true), []);
  const closeComposition = useCallback(() => setCompositionOpen(false), []);

  const rootClassName = lockViewport
    ? "h-dvh w-full overflow-hidden bg-slate-50 text-slate-900 antialiased"
    : "min-h-screen w-full overflow-x-hidden bg-slate-50 pb-24 text-slate-900 antialiased lg:pb-8";
  const shellClassName = lockViewport ? "flex h-dvh min-w-0 overflow-hidden" : "flex min-h-screen min-w-0";
  const contentClassName = lockViewport
    ? "flex h-dvh min-w-0 flex-1 flex-col overflow-hidden pt-14 lg:ml-64"
    : "flex min-h-screen min-w-0 flex-1 flex-col pt-14 lg:ml-64";
  const mainClassName = lockViewport ? "min-h-0 min-w-0 flex-1 overflow-hidden" : "min-w-0 flex-1";

  return (
    <div className={rootClassName}>
      <AppTopBar avatarFallback={avatarFallback} onLogout={onLogout} />
      <div className={shellClassName}>
        <AppSideNav
          activeItem={activeNav}
          onNewMeal={openAddMeal}
          onCompositionClick={openComposition}
        />
        <div className={contentClassName}>
          <main className={mainClassName}>
            <AddMealOpenProvider onOpen={openAddMeal}>{renderChildren()}</AddMealOpenProvider>
          </main>
        </div>
      </div>

      {showMobileFab ? (
        <button
          type="button"
          onClick={openAddMeal}
          className="fixed bottom-24 right-4 z-[45] flex h-14 w-14 items-center justify-center rounded-full bg-green-600 text-white shadow-lg transition hover:bg-green-700 active:scale-95 lg:hidden"
          aria-label="Добавить прием пищи"
        >
          <Plus className="h-7 w-7" aria-hidden strokeWidth={2.5} />
        </button>
      ) : null}

      <AppMobileBottomNav activeItem={activeNav} onCompositionClick={openComposition} />

      <CompositionLabelModal open={compositionOpen} onClose={closeComposition} />

      <AddMealModal
        open={addMealOpen}
        onClose={closeAddMeal}
        onMealSaved={onMealSaved}
        mealLocalDate={mealLocalDate}
      />
    </div>
  );
}
