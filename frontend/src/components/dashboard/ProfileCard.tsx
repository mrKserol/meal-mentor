import { User } from "lucide-react";

import type { User as UserType } from "../../types/auth";

import { getActivityLevelLabel, getGoalLabel } from "../../utils/profileLabels";

interface ProfileCardProps {
  user: UserType | null;
}

function formatWeightKg(value?: number | null): string {
  if (value == null || Number.isNaN(Number(value))) {
    return "Не указано";
  }
  const n = Number(value);
  return `${Number.isInteger(n) ? n : n.toFixed(1)} kg`;
}

export function ProfileCard({ user }: ProfileCardProps) {
  const displayName =
    user?.first_name?.trim() || user?.username?.trim() || user?.email?.trim()?.split("@")[0] || "Профиль";

  return (
    <div className="rounded-xl border border-outline-variant bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-low">
          <User className="h-6 w-6 text-on-surface-variant" aria-hidden />
        </div>
        <h3 className="font-h3 text-h3 text-on-surface">Мой профиль</h3>
      </div>
      <p className="mb-4 truncate text-body-md font-medium text-on-surface">{displayName}</p>

      <div className="space-y-4 text-body-md">
        <div className="flex items-center justify-between border-b border-surface-container-low pb-3">
          <span className="text-on-surface-variant">Текущий вес</span>
          <span className="font-bold text-on-surface">{formatWeightKg(user?.weight_kg ?? null)}</span>
        </div>
        <div className="flex items-center justify-between border-b border-surface-container-low pb-3">
          <span className="text-on-surface-variant">Целевой вес</span>
          <span className="font-bold text-on-surface">{formatWeightKg(user?.target_weight_kg ?? null)}</span>
        </div>
        <div className="flex items-center justify-between border-b border-surface-container-low pb-3">
          <span className="text-on-surface-variant">Цель</span>
          <span className="font-bold text-primary">{getGoalLabel(user?.goal)}</span>
        </div>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
          <span className="shrink-0 text-on-surface-variant">Активность</span>
          <span className="text-right font-bold text-on-surface sm:max-w-[60%]">
            {getActivityLevelLabel(user?.activity_level)}
          </span>
        </div>
      </div>
    </div>
  );
}
