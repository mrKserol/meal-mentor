import { formatIntRu, formatMacroGramsRu } from "../../utils/recentMeals";

type Props = {
  proteinG: number;
  fatG: number;
  carbsG: number;
  /** text-[10px] for compact cards, text-xs for modals */
  size?: "compact" | "normal";
  align?: "left" | "right";
  className?: string;
};

export function MealMacroLines({ proteinG, fatG, carbsG, size = "compact", align = "right", className = "" }: Props) {
  const text = size === "compact" ? "text-[10px] leading-tight" : "text-xs leading-snug";
  const alignCls = align === "right" ? "text-right" : "text-left";
  return (
    <div className={`${text} text-slate-500 ${alignCls} ${className}`}>
      <div>Б: {formatIntRu(proteinG)} г</div>
      <div>Ж: {formatIntRu(fatG)} г</div>
      <div>У: {formatIntRu(carbsG)} г</div>
    </div>
  );
}

export function MealMacroInline({
  proteinG,
  fatG,
  carbsG,
  fiberG,
  className = "",
}: {
  proteinG: number;
  fatG: number;
  carbsG: number;
  /** If set, appends «Клетчатка» (dietary fiber), grams. */
  fiberG?: number | null;
  className?: string;
}) {
  const base = `Б: ${formatIntRu(proteinG)} г · Ж: ${formatIntRu(fatG)} г · У: ${formatIntRu(carbsG)} г`;
  const fib =
    fiberG !== undefined && fiberG !== null ? ` · Клетчатка: ${formatMacroGramsRu(fiberG)} г` : "";
  return (
    <span className={`text-slate-600 ${className}`.trim()}>
      {base}
      {fib}
    </span>
  );
}
