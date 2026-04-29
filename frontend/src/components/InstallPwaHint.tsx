import { useEffect, useMemo, useState } from "react";

const LS_KEY = "meal_mentor_pwa_hint_dismissed_v1";

export function InstallPwaHint() {
  const [shouldShow, setShouldShow] = useState(false);

  const isStandalone = useMemo(() => {
    const nav = window.navigator as unknown as { standalone?: boolean };
    const standaloneViaIOS = nav.standalone === true;
    const standaloneViaMedia = window.matchMedia?.("(display-mode: standalone)")?.matches ?? false;
    return standaloneViaIOS || standaloneViaMedia;
  }, []);

  useEffect(() => {
    const ua = navigator.userAgent || "";
    const isIOS = /iPad|iPhone|iPod/.test(ua);
    const isSafari =
      isIOS && /Safari/.test(ua) && !/CriOS|FxiOS|OPiOS/.test(ua);

    if (!isSafari || isStandalone) {
      setShouldShow(false);
      return;
    }

    if (localStorage.getItem(LS_KEY) === "1") {
      setShouldShow(false);
      return;
    }

    setShouldShow(true);
  }, [isStandalone]);

  if (!shouldShow) return null;

  return (
    <div className="fixed bottom-2 left-0 right-0 flex justify-center z-50 pointer-events-none">
      <div className="max-w-[90vw] bg-surface-container-lowest border border-outline-variant/60 rounded-lg shadow-[0_10px_30px_rgba(0,0,0,0.08)] px-4 py-2">
        <p className="text-[12px] leading-4 text-on-secondary-container">
          Чтобы установить Meal Mentor как приложение: нажмите <b>Поделиться</b> → <b>На экран «Домой»</b>
        </p>
      </div>
    </div>
  );
}

