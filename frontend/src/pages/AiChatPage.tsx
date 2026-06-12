import axios from "axios";
import { Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  acceptAiChatDisclaimer,
  getAiChatBootstrap,
  getAiChatLimits,
  getAiChatMessagesPage,
  sendAiChatMessage,
  type AiChatLimitsResponse,
  type AiChatMessage,
} from "../api/aiChatApi";
import MessageMarkdown from "../components/ai-chat/MessageMarkdown";
import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../hooks/useAuth";

const quickCommands = [
  "Проанализируй мой рацион",
  "Как мне добрать белок?",
  "Почему у меня перебор по жирам?",
];

const INPUT_LIMIT = 2000;

function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error) && error.response?.data?.detail != null) {
    return String(error.response.data.detail);
  }
  return fallback;
}

export function AiChatPage() {
  const navigate = useNavigate();
  const { user, validateSession, getAccessToken, logout } = useAuth();
  const [messages, setMessages] = useState<AiChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [disclaimerRequired, setDisclaimerRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limits, setLimits] = useState<AiChatLimitsResponse | null>(null);
  const [accessMessage, setAccessMessage] = useState<string | null>(null);
  const [oldestMessageId, setOldestMessageId] = useState<number | null>(null);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const shouldScrollToBottomRef = useRef(false);

  const avatarFallback = useMemo(() => {
    return user?.first_name?.trim()?.[0] ?? user?.username?.trim()?.[0] ?? user?.email?.trim()?.[0] ?? "U";
  }, [user]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior, block: "end" });
    });
  }, []);

  const bootstrap = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setAccessMessage(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        navigate("/login", { replace: true });
        return;
      }
      const token = getAccessToken();
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const data = await getAiChatBootstrap(token);
      setDisclaimerRequired(data.disclaimer_required);
      shouldScrollToBottomRef.current = true;
      setMessages(data.messages);
      setOldestMessageId(data.oldest_message_id);
      setHasMoreMessages(data.has_more_messages);
      if (!data.disclaimer_required) {
        const nextLimits = await getAiChatLimits(token);
        setLimits(nextLimits);
        if (!nextLimits.enabled) {
          setAccessMessage("ИИ-чат недоступен на вашем тарифе.");
        } else if (nextLimits.remaining_today === 0) {
          setAccessMessage("Дневной лимит сообщений в ИИ-чате исчерпан. Лимит обновится завтра.");
        }
      }
    } catch (err) {
      const message = errorMessage(err, "Не удалось загрузить чат. Обновите страницу или попробуйте позже.");
      if (axios.isAxiosError(err) && err.response?.status === 403) {
        setDisclaimerRequired(false);
        setAccessMessage(message);
        setMessages([]);
        setOldestMessageId(null);
        setHasMoreMessages(false);
      } else {
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken, navigate, validateSession]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (!shouldScrollToBottomRef.current) return;
    if (isLoading || disclaimerRequired || (accessMessage && limits?.enabled === false)) return;
    shouldScrollToBottomRef.current = false;
    scrollToBottom("auto");
  }, [accessMessage, disclaimerRequired, isLoading, limits?.enabled, messages, scrollToBottom]);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const handleAcceptDisclaimer = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        navigate("/login", { replace: true });
        return;
      }
      const token = getAccessToken();
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      await acceptAiChatDisclaimer(token);
      await bootstrap();
    } catch (err) {
      setError(errorMessage(err, "Не удалось сохранить согласие. Попробуйте ещё раз."));
    } finally {
      setIsLoading(false);
    }
  }, [bootstrap, getAccessToken, navigate, validateSession]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isSending || accessMessage || limits?.enabled === false || limits?.remaining_today === 0) return;
    setIsSending(true);
    setError(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        navigate("/login", { replace: true });
        return;
      }
      const token = getAccessToken();
      if (!token) {
        navigate("/login", { replace: true });
        return;
      }
      const data = await sendAiChatMessage(token, text);
      shouldScrollToBottomRef.current = true;
      setMessages((prev) => [...prev, data.user_message, data.assistant_message]);
      setInput("");
      const nextLimits = await getAiChatLimits(token);
      setLimits(nextLimits);
      if (nextLimits.remaining_today === 0) {
        setAccessMessage("Дневной лимит сообщений в ИИ-чате исчерпан. Лимит обновится завтра.");
      }
    } catch (err) {
      const message = errorMessage(err, "Не удалось получить ответ Meal-Mentor. Попробуйте ещё раз.");
      if (axios.isAxiosError(err) && err.response?.status === 403) {
        setAccessMessage(message);
      } else {
        setError(message);
      }
    } finally {
      setIsSending(false);
    }
  }, [accessMessage, getAccessToken, input, isSending, limits?.enabled, limits?.remaining_today, navigate, validateSession]);

  const loadOlderMessages = useCallback(async () => {
    if (!hasMoreMessages || isLoadingOlder || !oldestMessageId) return;
    const token = getAccessToken();
    if (!token) return;

    const container = messagesContainerRef.current;
    const previousScrollHeight = container?.scrollHeight ?? 0;
    const previousScrollTop = container?.scrollTop ?? 0;

    setIsLoadingOlder(true);
    try {
      const page = await getAiChatMessagesPage(token, oldestMessageId, 10);
      setMessages((prev) => {
        const existingIds = new Set(prev.map((message) => message.id));
        const newMessages = page.messages.filter((message) => !existingIds.has(message.id));
        return [...newMessages, ...prev];
      });
      setOldestMessageId(page.oldest_message_id);
      setHasMoreMessages(page.has_more);

      requestAnimationFrame(() => {
        const updatedContainer = messagesContainerRef.current;
        if (!updatedContainer) return;
        const newScrollHeight = updatedContainer.scrollHeight;
        updatedContainer.scrollTop = newScrollHeight - previousScrollHeight + previousScrollTop;
      });
    } catch (err) {
      setError(errorMessage(err, "Не удалось загрузить старые сообщения."));
    } finally {
      setIsLoadingOlder(false);
    }
  }, [getAccessToken, hasMoreMessages, isLoadingOlder, oldestMessageId]);

  const limitsText = useMemo(() => {
    if (!limits?.enabled) return null;
    if (limits.daily_limit === -1) {
      return `Сообщений сегодня: ${limits.used_today}, без дневного лимита`;
    }
    const remaining = limits.remaining_today ?? 0;
    return `Осталось сообщений сегодня: ${remaining} из ${limits.daily_limit}`;
  }, [limits]);

  return (
    <AppShell
      activeNav="ai-chat"
      avatarFallback={avatarFallback}
      onLogout={handleLogout}
      showMobileFab={false}
      lockViewport
    >
      <div className="mx-auto flex h-full min-h-0 w-full max-w-6xl flex-col gap-4 overflow-hidden p-4 pb-[calc(7rem+env(safe-area-inset-bottom))] lg:p-8 lg:pb-8">
        <header className="shrink-0">
          <h1 className="text-2xl font-bold text-slate-950">Чат с ИИ</h1>
          <p className="mt-1 text-sm text-slate-500">Анализ дневника питания</p>
        </header>

        {isLoading ? (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 text-slate-500">
            Загружаем чат...
          </div>
        ) : disclaimerRequired ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
              <h2 className="text-xl font-bold text-slate-950">Перед началом</h2>
              <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
                <p>
                  Meal-Mentor помогает анализировать дневник питания, замечать возможные паттерны и подсказывать общие
                  направления для улучшения рациона.
                </p>
                <p>
                  Ответы ИИ могут содержать ошибки и не являются медицинской консультацией, диагнозом или назначением
                  лечения.
                </p>
                <p>
                  По вопросам заболеваний, анализов, лекарств, добавок, резких изменений веса, беременности,
                  расстройств пищевого поведения или плохого самочувствия обратитесь к квалифицированному специалисту.
                </p>
              </div>
              {error ? <p className="mt-4 text-sm font-medium text-red-600">{error}</p> : null}
              <button
                type="button"
                onClick={() => void handleAcceptDisclaimer()}
                className="mt-6 rounded-xl bg-green-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
              >
                Я понимаю
              </button>
            </div>
          </div>
        ) : accessMessage && limits?.enabled === false ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="max-w-xl rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm sm:p-8">
              <h2 className="text-xl font-bold text-slate-950">ИИ-чат недоступен</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">{accessMessage}</p>
            </div>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 overflow-hidden overscroll-none">
            <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div ref={messagesContainerRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-4 sm:p-5">
                {hasMoreMessages ? (
                  <div className="flex justify-center py-2">
                    <button
                      type="button"
                      onClick={() => void loadOlderMessages()}
                      disabled={isLoadingOlder}
                      className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isLoadingOlder ? "Загружаю..." : "Показать старые сообщения"}
                    </button>
                  </div>
                ) : null}
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                        message.role === "user"
                          ? "bg-green-600 text-white"
                          : "border border-slate-100 bg-slate-50 text-slate-800"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <MessageMarkdown content={message.content} />
                      ) : (
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      )}
                    </div>
                  </div>
                ))}
                {isSending ? <p className="text-sm text-slate-500">Meal-Mentor печатает...</p> : null}
                <div ref={messagesEndRef} />
              </div>

              {accessMessage ? (
                <p className="border-t border-amber-100 bg-amber-50 px-4 py-2 text-sm text-amber-800">{accessMessage}</p>
              ) : null}
              {error ? <p className="border-t border-red-100 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p> : null}

              <div className="shrink-0 border-t border-slate-100 bg-white p-3 sm:p-4">
                <div className="mb-3">
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {quickCommands.map((command) => (
                      <button
                        key={command}
                        type="button"
                        onClick={() => setInput(command)}
                        disabled={isSending || Boolean(accessMessage)}
                        className="max-w-[15rem] shrink-0 truncate rounded-full border border-slate-200 bg-white px-3 py-2 text-left text-xs font-medium text-slate-700 transition hover:border-green-200 hover:bg-green-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {command}
                      </button>
                    ))}
                  </div>
                </div>

                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void handleSend();
                    }
                  }}
                  rows={2}
                  maxLength={INPUT_LIMIT}
                  disabled={isSending || Boolean(accessMessage)}
                  placeholder="Напишите вопрос о дневнике питания..."
                  className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none ring-green-100 focus:border-green-600 focus:ring-2"
                />
                <div className="mt-2 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <span className="block text-xs text-slate-400">{input.length}/{INPUT_LIMIT}</span>
                    {limitsText ? <p className="text-xs font-medium text-slate-500">{limitsText}</p> : null}
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleSend()}
                    disabled={!input.trim() || isSending || Boolean(accessMessage)}
                    className="inline-flex items-center gap-2 rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" aria-hidden />
                    Отправить
                  </button>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
