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
  const progress = target > 0 ? Math.min(current / target, 1) : 0;
  const dashOffset = CIRC * (1 - progress);
  const pct = target > 0 ? Math.round(progress * 100) : 0;

  const currentFmt = Number.isInteger(current) ? String(current) : current.toFixed(1);
  const targetFmt = Number.isInteger(target) ? String(target) : target.toFixed(1);

  return (
    <div className="flex flex-col items-center rounded-xl bg-surface-container-low p-4">
      <div className="relative mb-2 h-20 w-20">
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
            className={ringClass}
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
        <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-on-surface">
          {pct}%
        </div>
      </div>
      <p className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">{label}</p>
      <p className="font-h3 text-h3 text-center text-on-surface">
        {currentFmt}
        {unit} / {targetFmt}
        {unit}
      </p>
    </div>
  );
}
