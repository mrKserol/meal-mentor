import { useState } from "react";
import { Droplets } from "lucide-react";

interface WaterButtonProps {
  saving: boolean;
  onRecord: (amountMl: number) => void;
  /** Extra classes for the outer wrapper (e.g. w-full, flex-1) */
  className?: string;
  /** Vertical padding variant — "md" (py-3, default) or "sm" (py-2.5) */
  size?: "md" | "sm";
}

export function WaterButton({ saving, onRecord, className = "", size = "md" }: WaterButtonProps) {
  const [ml, setMl] = useState(100);

  const py = size === "sm" ? "py-2" : "py-2.5";

  return (
    <div
      className={`flex items-stretch overflow-hidden rounded-xl border border-sky-200 bg-sky-50 ${className}`}
    >
      {/* Main tap area — records water */}
      <button
        type="button"
        disabled={saving}
        onClick={() => onRecord(ml)}
        className={`flex flex-1 items-center gap-2 pl-4 pr-2 ${py} text-sm font-semibold text-sky-900 transition hover:bg-sky-100 disabled:opacity-50`}
      >
        <Droplets className="h-4 w-4 shrink-0" aria-hidden />
        {saving ? "Сохранение…" : "Выпить воды"}
      </button>

      {/* Stepper — stops propagation so only amount changes */}
      <div className="flex items-center gap-0.5 border-l border-sky-200 px-2">
        <button
          type="button"
          disabled={saving || ml <= 50}
          onClick={(e) => {
            e.stopPropagation();
            setMl((v) => Math.max(50, v - 50));
          }}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-base font-bold text-sky-700 transition hover:bg-sky-100 disabled:opacity-30"
          aria-label="Уменьшить на 50 мл"
        >
          −
        </button>
        <span className="min-w-[2.25rem] select-none text-center text-sm font-semibold text-sky-900">
          {ml}
        </span>
        <button
          type="button"
          disabled={saving}
          onClick={(e) => {
            e.stopPropagation();
            setMl((v) => v + 50);
          }}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-base font-bold text-sky-700 transition hover:bg-sky-100 disabled:opacity-30"
          aria-label="Увеличить на 50 мл"
        >
          +
        </button>
        <span className="pr-1 text-sm font-medium text-sky-700">мл</span>
      </div>
    </div>
  );
}
