import { type ReactNode, useCallback, useRef, useState } from "react";

const DELETE_PANEL_PX = 96;

type SwipeDeleteRowProps = {
  children: ReactNode;
  onDelete: () => void;
  onOpen?: () => void;
  disabled?: boolean;
};

export function SwipeDeleteRow({ children, onDelete, onOpen, disabled }: SwipeDeleteRowProps) {
  const [offset, setOffset] = useState(0);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startOffset = useRef(0);
  const pointerId = useRef<number | null>(null);
  const maxAbsDx = useRef(0);
  const suppressOpen = useRef(false);
  const offsetRef = useRef(0);
  offsetRef.current = offset;

  const clamp = useCallback((v: number) => Math.min(0, Math.max(-DELETE_PANEL_PX, v)), []);

  const onPointerDown = (e: React.PointerEvent) => {
    if (disabled) return;
    if (e.button !== 0) return;
    dragging.current = true;
    startX.current = e.clientX;
    startOffset.current = offset;
    maxAbsDx.current = 0;
    suppressOpen.current = false;
    pointerId.current = e.pointerId;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current || pointerId.current !== e.pointerId) return;
    const dx = e.clientX - startX.current;
    maxAbsDx.current = Math.max(maxAbsDx.current, Math.abs(dx));
    if (maxAbsDx.current > 12) suppressOpen.current = true;
    setOffset(clamp(startOffset.current + dx));
  };

  const endDrag = (e: React.PointerEvent) => {
    if (pointerId.current !== e.pointerId) return;
    dragging.current = false;
    pointerId.current = null;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    setOffset((cur) => (cur < -DELETE_PANEL_PX / 2 ? -DELETE_PANEL_PX : 0));
  };

  const handleTap = () => {
    if (suppressOpen.current) return;
    if (offsetRef.current !== 0) {
      setOffset(0);
      return;
    }
    onOpen?.();
  };

  return (
    <div className="relative overflow-hidden border-b border-slate-100 last:border-b-0">
      <div
        className="absolute inset-y-0 right-0 z-0 flex w-[96px] items-stretch justify-stretch bg-red-600"
        aria-hidden={offset === 0}
      >
        <button
          type="button"
          disabled={disabled}
          onClick={(ev) => {
            ev.stopPropagation();
            void onDelete();
          }}
          className="w-full text-center text-sm font-bold text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          Удалить
        </button>
      </div>
      <div
        role={onOpen ? "button" : "presentation"}
        tabIndex={onOpen ? 0 : undefined}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClick={onOpen ? handleTap : undefined}
        onKeyDown={
          onOpen
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onOpen();
                }
              }
            : undefined
        }
        style={{
          transform: `translateX(${offset}px)`,
          touchAction: "pan-y",
        }}
        className={`relative z-10 bg-white ${onOpen ? "cursor-pointer" : ""}`}
      >
        {children}
      </div>
    </div>
  );
}
