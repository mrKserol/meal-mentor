import { useEffect, useRef } from "react";

import type { TelegramAuthPayload } from "../types/auth";

declare global {
  interface Window {
    onTelegramAuth?: (user: Omit<TelegramAuthPayload, "timezone">) => void;
  }
}

interface TelegramLoginButtonProps {
  botUsername: string;
  onAuth: (payload: TelegramAuthPayload) => void;
}

export function TelegramLoginButton({ botUsername, onAuth }: TelegramLoginButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !botUsername) {
      return;
    }

    window.onTelegramAuth = (telegramUser) => {
      onAuth({
        ...telegramUser,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      });
    };

    containerRef.current.innerHTML = "";
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-userpic", "false");
    script.setAttribute("data-request-access", "write");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    containerRef.current.appendChild(script);

    return () => {
      window.onTelegramAuth = undefined;
    };
  }, [botUsername, onAuth]);

  if (!botUsername) {
    return (
      <button
        type="button"
        disabled
        className="w-full bg-secondary-container text-on-secondary-container py-3 rounded-lg text-sm cursor-not-allowed opacity-70"
      >
        Telegram login недоступен (нет VITE_TELEGRAM_BOT_USERNAME)
      </button>
    );
  }

  return <div ref={containerRef} className="flex justify-center" />;
}
