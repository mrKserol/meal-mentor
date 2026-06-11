export interface CircularMacroProgressProps {
  label: string;
  current: number;
  target: number;
  unit: string;
  /** Tailwind ring color class (stroke uses currentColor) */
  ringClass?: string;
}

const R = 34;
const CIRC = 2 * Math.PI * R;

export function CircularMacroProgress({
  label,
  current,
  target,
  unit,
  ringClass = "text-primary",
}: CircularMacroProgressProps) {
  const ratio = target > 0 ? current / target : 0;
  const progress = Math.min(Math.max(ratio, 0), 1);
  const dashOffset = CIRC * (1 - progress);
  const pct = target > 0 ? Math.round(ratio * 100) : 0;
  const isOverTarget = pct > 100;

  const currentFmt = Number.isInteger(current) ? String(current) : current.toFixed(1);
  const targetFmt = Number.isInteger(target) ? String(target) : target.toFixed(1);

  return (
    <div className="flex min-w-0 flex-col items-center rounded-xl bg-surface-container-low p-2 sm:p-4">
      <div className="relative mb-1 h-14 w-14 sm:mb-2 sm:h-20 sm:w-20">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 80 80" aria-hidden>
          <circle
            className="text-surface-container-highest"
            cx="40"
            cy="40"
            r={R}
            fill="transparent"
            stroke="currentColor"
            strokeWidth="8"
          />
          <circle
            className={isOverTarget ? "text-orange-500" : ringClass}
            cx="40"
            cy="40"
            r={R}
            fill="transparent"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={dashOffset}
          />
        </svg>
        <div
          className={`absolute inset-0 flex items-center justify-center text-[10px] font-bold sm:text-sm ${
            isOverTarget ? "text-orange-600" : "text-on-surface"
          }`}
        >
          {pct}%
        </div>
      </div>
      <p className="text-[10px] font-medium uppercase tracking-wide text-on-surface-variant sm:font-label-sm sm:text-label-sm sm:tracking-wider">
        {label}
      </p>
      <p className="text-center text-[11px] font-semibold leading-tight text-on-surface sm:font-h3 sm:text-h3">
        {currentFmt}
        {unit} / {targetFmt}
        {unit}
      </p>
    </div>
  );
}
