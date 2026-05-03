import { createContext, useContext, type ReactNode } from "react";

const AddMealOpenContext = createContext<(() => void) | null>(null);

export function AddMealOpenProvider({ children, onOpen }: { children: ReactNode; onOpen: () => void }) {
  return <AddMealOpenContext.Provider value={onOpen}>{children}</AddMealOpenContext.Provider>;
}

/** Возвращает функцию открытия модалки «Добавить прием пищи» внутри AppShell, иначе null. */
export function useOpenAddMeal(): (() => void) | null {
  return useContext(AddMealOpenContext);
}
