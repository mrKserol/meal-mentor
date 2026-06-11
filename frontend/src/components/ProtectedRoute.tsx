import { useCallback, useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { getConsentStatus } from "../api/consentsApi";
import { DisclaimerScreen } from "./disclaimer/DisclaimerScreen";
import { useAuth } from "../hooks/useAuth";
import type { ConsentStatus } from "../types/consents";

const DISCLAIMER_ACCEPTED_KEY = "meal_mentor_disclaimer_accepted";
const DISCLAIMER_VERSION_KEY = "meal_mentor_disclaimer_version";

function getCachedDisclaimerVersion(): string | null {
  return localStorage.getItem(DISCLAIMER_VERSION_KEY);
}

function hasCachedDisclaimerAccepted(): boolean {
  return localStorage.getItem(DISCLAIMER_ACCEPTED_KEY) === "true";
}

function cacheDisclaimerAccepted(version: string): void {
  localStorage.setItem(DISCLAIMER_ACCEPTED_KEY, "true");
  localStorage.setItem(DISCLAIMER_VERSION_KEY, version);
}

function clearDisclaimerCache(): void {
  localStorage.removeItem(DISCLAIMER_ACCEPTED_KEY);
  localStorage.removeItem(DISCLAIMER_VERSION_KEY);
}

export function ProtectedRoute() {
  const { getAccessToken, isAuthenticated, isLoading, validateSession } = useAuth();
  const location = useLocation();
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [consentLoading, setConsentLoading] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);

  const checkConsent = useCallback(
    async (isCancelled: () => boolean = () => false) => {
      const cachedAccepted = hasCachedDisclaimerAccepted();
      const cachedVersion = getCachedDisclaimerVersion();

      setConsentLoading(true);
      setConsentError(null);

      try {
        const sessionOk = await validateSession();
        if (isCancelled()) return;

        if (!sessionOk) {
          clearDisclaimerCache();
          setConsentError("Сессия истекла. Войдите заново.");
          return;
        }

        const accessToken = getAccessToken();
        if (!accessToken) {
          clearDisclaimerCache();
          setConsentError("Сессия не найдена. Войдите заново.");
          return;
        }

        const status = await getConsentStatus(accessToken);
        if (isCancelled()) return;

        setConsentStatus(status);
        if (status.accepted && !status.required) {
          cacheDisclaimerAccepted(status.current_version);
        } else {
          clearDisclaimerCache();
        }
      } catch {
        if (isCancelled()) return;

        if (cachedAccepted && cachedVersion) {
          setConsentStatus({
            required: false,
            accepted: true,
            consent_type: "disclaimer",
            current_version: cachedVersion,
            accepted_at: null,
          });
          setConsentError(null);
          return;
        }

        setConsentError("Не удалось проверить согласие с дисклеймером. Проверьте интернет и попробуйте ещё раз.");
      } finally {
        if (!isCancelled()) {
          setConsentLoading(false);
        }
      }
    },
    [getAccessToken, validateSession],
  );

  useEffect(() => {
    if (isLoading || !isAuthenticated || location.pathname === "/disclaimer") {
      return;
    }

    let cancelled = false;
    void checkConsent(() => cancelled);

    return () => {
      cancelled = true;
    };
  }, [checkConsent, isAuthenticated, isLoading, location.pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <p className="text-on-surface-variant font-body-md">Проверка сессии...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (location.pathname === "/disclaimer") {
    return <Outlet />;
  }

  if (consentError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface p-6">
        <div className="max-w-md text-center">
          <p className="text-on-surface-variant font-body-md">{consentError}</p>
          <button
            type="button"
            onClick={() => void checkConsent()}
            className="mt-4 rounded-xl bg-green-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  if (consentLoading || !consentStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <p className="text-on-surface-variant font-body-md">Проверка согласия...</p>
      </div>
    );
  }

  if (consentStatus.required) {
    return (
      <DisclaimerScreen
        currentVersion={consentStatus.current_version}
        onAccepted={() => {
          cacheDisclaimerAccepted(consentStatus.current_version);
          setConsentStatus({
            ...consentStatus,
            required: false,
            accepted: true,
            accepted_at: new Date().toISOString(),
          });
        }}
      />
    );
  }

  return <Outlet />;
}
