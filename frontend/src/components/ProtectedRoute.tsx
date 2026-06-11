import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { getConsentStatus } from "../api/consentsApi";
import { DisclaimerScreen } from "./disclaimer/DisclaimerScreen";
import { useAuth } from "../hooks/useAuth";
import type { ConsentStatus } from "../types/consents";

export function ProtectedRoute() {
  const { getAccessToken, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [consentLoading, setConsentLoading] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading || !isAuthenticated || location.pathname === "/disclaimer") {
      return;
    }

    let cancelled = false;
    const checkConsent = async () => {
      const accessToken = getAccessToken();
      if (!accessToken) {
        setConsentError("Сессия не найдена. Войдите заново.");
        return;
      }

      setConsentLoading(true);
      setConsentError(null);
      try {
        const status = await getConsentStatus(accessToken);
        if (!cancelled) {
          setConsentStatus(status);
        }
      } catch {
        if (!cancelled) {
          setConsentError("Не удалось проверить согласие с дисклеймером. Попробуйте обновить страницу.");
        }
      } finally {
        if (!cancelled) {
          setConsentLoading(false);
        }
      }
    };

    void checkConsent();

    return () => {
      cancelled = true;
    };
  }, [getAccessToken, isAuthenticated, isLoading, location.pathname]);

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
        <p className="max-w-md text-center text-on-surface-variant font-body-md">{consentError}</p>
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
        onAccepted={() =>
          setConsentStatus({
            ...consentStatus,
            required: false,
            accepted: true,
            accepted_at: new Date().toISOString(),
          })
        }
      />
    );
  }

  return <Outlet />;
}
