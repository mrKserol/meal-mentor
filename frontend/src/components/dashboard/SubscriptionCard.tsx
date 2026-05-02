import { Star } from "lucide-react";

import { getSubscriptionLabel, subscriptionIsFree } from "../../utils/profileLabels";

interface SubscriptionCardProps {
  subscriptionStatus?: string | null;
  onUpgradeClick?: () => void;
}

export function SubscriptionCard({
  subscriptionStatus,
  onUpgradeClick,
}: SubscriptionCardProps) {
  const isFree = subscriptionIsFree(subscriptionStatus);
  const label = getSubscriptionLabel(subscriptionStatus);

  return (
    <div className="relative overflow-hidden rounded-xl bg-inverse-surface px-6 py-6 text-inverse-on-surface shadow-lg">
      <div className="relative z-10">
        <div className="mb-3 flex items-center gap-2">
          <Star className="h-6 w-6 text-primary-container" aria-hidden />
          <h3 className="font-h3 text-h3">Подписка</h3>
        </div>
        <p className="mb-1 font-body-md text-white/95">
          Текущий тариф: <span className="font-bold">{label}</span>
        </p>
        {isFree ? (
          <>
            <p className="mb-6 text-body-md opacity-85">
              Оформите подписку, чтобы разблокировать расширенные функции ИИ-помощника.
            </p>
            <button
              type="button"
              onClick={onUpgradeClick}
              className="w-full rounded-lg bg-primary-container py-3 font-bold text-on-primary transition hover:brightness-105"
            >
              Upgrade Now
            </button>
          </>
        ) : (
          <p className="pt-2 text-body-md opacity-95">Ваш тариф активен.</p>
        )}
      </div>
      <div className="pointer-events-none absolute -bottom-10 -right-10 h-36 w-36 rounded-full bg-primary/35 blur-3xl" />
    </div>
  );
}
