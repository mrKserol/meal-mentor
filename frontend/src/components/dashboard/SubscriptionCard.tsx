import { Star } from "lucide-react";
import { useCallback, useState } from "react";

import { getSubscriptionLabel, subscriptionIsFree } from "../../utils/profileLabels";

const BETA_CONTACT_EMAIL = "kserolik63@yandex.com";

interface SubscriptionCardProps {
  subscriptionStatus?: string | null;
  onUpgradeClick?: () => void;
}

export function SubscriptionCard({
  subscriptionStatus,
  onUpgradeClick,
}: SubscriptionCardProps) {
  const [betaInfoOpen, setBetaInfoOpen] = useState(false);
  const isFree = subscriptionIsFree(subscriptionStatus);
  const label = getSubscriptionLabel(subscriptionStatus);

  const handleUpgradeClick = useCallback(() => {
    if (onUpgradeClick) {
      onUpgradeClick();
      return;
    }
    setBetaInfoOpen(true);
  }, [onUpgradeClick]);

  return (
  <>
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
              onClick={handleUpgradeClick}
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

    {betaInfoOpen ? (
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="beta-info-title"
        onClick={() => setBetaInfoOpen(false)}
      >
        <div
          className="w-full max-w-md rounded-xl bg-white p-6 text-slate-900 shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          <h4 id="beta-info-title" className="text-lg font-semibold">
            Бета-тестирование
          </h4>
          <p className="mt-3 text-base leading-relaxed text-slate-600">
            В данный момент приложение в стадии бета-тестирования. Заявки в участии можно оставить на{" "}
            <a
              href={`mailto:${BETA_CONTACT_EMAIL}`}
              className="font-medium text-green-700 underline hover:text-green-800"
            >
              {BETA_CONTACT_EMAIL}
            </a>
            .
          </p>
          <button
            type="button"
            onClick={() => setBetaInfoOpen(false)}
            className="mt-6 w-full rounded-lg bg-green-600 py-2.5 font-semibold text-white hover:bg-green-700"
          >
            Понятно
          </button>
        </div>
      </div>
    ) : null}
  </>
  );
}
