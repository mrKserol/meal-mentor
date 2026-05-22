import type { CuratorUserProfile } from "../../api/curatorApi";
import {
  ageYearsFromBirthDate,
  formatWeightKgRu,
  getActivityLevelLabel,
} from "../../utils/profileLabels";

function buildMainLine(profile: CuratorUserProfile): string {
  const segments: string[] = [];
  const name = profile.first_name?.trim() || "Пользователь";
  segments.push(name);

  const age = ageYearsFromBirthDate(profile.birth_date);
  if (age != null) {
    segments.push(`${age} лет`);
  }
  if (profile.height_cm != null) {
    segments.push(`${profile.height_cm} см`);
  }
  if (profile.weight_kg != null) {
    segments.push(formatWeightKgRu(profile.weight_kg));
  }

  return segments.join(", ");
}

export interface CuratorUserProfileSummaryProps {
  profile: CuratorUserProfile | null;
  loading?: boolean;
}

export function CuratorUserProfileSummary({ profile, loading }: CuratorUserProfileSummaryProps) {
  if (loading && !profile) {
    return <p className="text-sm text-slate-500">Загружаем профиль…</p>;
  }
  if (!profile) {
    return null;
  }

  return (
    <div className="min-w-0 space-y-0.5 text-sm text-slate-600">
      <p className="font-semibold leading-snug text-slate-900">{buildMainLine(profile)}</p>
      <p>
        <span className="text-slate-500">Желаемый вес:</span>{" "}
        <span className="font-medium text-slate-800">{formatWeightKgRu(profile.target_weight_kg)}</span>
      </p>
      <p>
        <span className="text-slate-500">Активность:</span>{" "}
        <span className="font-medium text-slate-800">{getActivityLevelLabel(profile.activity_level)}</span>
      </p>
    </div>
  );
}
