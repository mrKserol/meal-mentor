import axios from "axios";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, ImagePlus, Loader2, X } from "lucide-react";

import { analyzeProductLabel } from "../../api/authApi";
import { useAuth } from "../../hooks/useAuth";

type Phase = "pick" | "loading" | "done" | "error";

const INVITE =
  "Сфотографируй этикетку с составом продукта, и я проанализирую ингредиенты";

interface CompositionLabelModalProps {
  open: boolean;
  onClose: () => void;
}

export function CompositionLabelModal({ open, onClose }: CompositionLabelModalProps) {
  const { validateSession, getAccessToken } = useAuth();
  const [phase, setPhase] = useState<Phase>("pick");
  const [resultText, setResultText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setPhase("pick");
    setResultText("");
    setErrorMessage(null);
  }, []);

  useEffect(() => {
    if (open) reset();
  }, [open, reset]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const runAnalysis = async (file: File) => {
    setPhase("loading");
    setErrorMessage(null);
    try {
      const ok = await validateSession();
      if (!ok) {
        throw new Error("Сессия истекла. Войдите снова.");
      }
      const token = getAccessToken();
      if (!token) {
        throw new Error("Нет авторизации.");
      }
      const res = await analyzeProductLabel(token, file);
      setResultText(res.text);
      setPhase("done");
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const d = err.response?.data as { detail?: unknown } | undefined;
        let detail = "";
        if (d && typeof d === "object" && "detail" in d) {
          const raw = d.detail;
          detail = Array.isArray(raw)
            ? raw.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: unknown }).msg) : String(x))).join(" ")
            : String(raw ?? "");
        }
        setErrorMessage(detail || err.message || "Не удалось проанализировать изображение.");
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Не удалось проанализировать изображение.");
      }
      setPhase("error");
    }
  };

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    void runAnalysis(file);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/45 p-4 sm:items-center"
      role="presentation"
      onMouseDown={(ev) => {
        if (ev.target === ev.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="composition-label-title"
        className="flex max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 id="composition-label-title" className="text-lg font-semibold text-slate-900">
            Состав продукта
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
            aria-label="Закрыть"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {phase === "pick" ? (
            <div className="space-y-5">
              <p className="text-center text-base leading-relaxed text-slate-700">{INVITE}</p>
              <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-green-600 bg-green-600 px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-green-700 active:scale-[0.99]"
                >
                  <Camera className="h-5 w-5 shrink-0" aria-hidden />
                  Сфотографировать
                </button>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 font-semibold text-slate-800 shadow-sm transition hover:border-green-200 hover:bg-green-50/60 active:scale-[0.99]"
                >
                  <ImagePlus className="h-5 w-5 shrink-0" aria-hidden />
                  Загрузить файл
                </button>
              </div>
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/*"
                capture="environment"
                className="sr-only"
                onChange={onFileChange}
              />
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/*"
                className="sr-only"
                onChange={onFileChange}
              />
            </div>
          ) : null}

          {phase === "loading" ? (
            <div className="flex flex-col items-center justify-center gap-4 py-10 text-slate-600">
              <Loader2 className="h-10 w-10 animate-spin text-green-600" aria-hidden />
              <p className="text-center text-sm font-medium">Анализирую этикетку…</p>
            </div>
          ) : null}

          {phase === "done" ? (
            <div className="space-y-4">
              <pre className="whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
                {resultText}
              </pre>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={reset}
                  className="flex-1 rounded-xl border border-slate-200 bg-white py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
                >
                  Другое фото
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition hover:bg-green-700"
                >
                  Закрыть
                </button>
              </div>
            </div>
          ) : null}

          {phase === "error" ? (
            <div className="space-y-4">
              <p className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-800">
                {errorMessage}
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={reset}
                  className="flex-1 rounded-xl border border-slate-200 bg-white py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
                >
                  Попробовать снова
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 rounded-xl bg-slate-100 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-200"
                >
                  Закрыть
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
