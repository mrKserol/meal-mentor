import { useRef, useState, type ReactNode } from "react";

const SWIPE_OPEN = -88;
const SWIPE_TRIGGER = -48;

type SwipeableUserRowProps = {
  children: ReactNode;
  onDeleteRequest: () => void;
  disabled?: boolean;
};

export function SwipeableUserRow({ children, onDeleteRequest, disabled = false }: SwipeableUserRowProps) {
  const [offsetX, setOffsetX] = useState(0);
  const startX = useRef(0);
  const startOffset = useRef(0);
  const dragging = useRef(false);

  const clampOffset = (value: number) => Math.max(SWIPE_OPEN, Math.min(0, value));

  const finishDrag = (clientX: number) => {
    if (!dragging.current || disabled) return;
    dragging.current = false;
    const delta = clientX - startX.current;
    const next = clampOffset(startOffset.current + delta);
    setOffsetX(next <= SWIPE_TRIGGER ? SWIPE_OPEN : 0);
  };

  const onTouchStart = (e: React.TouchEvent) => {
    if (disabled) return;
    dragging.current = true;
    startX.current = e.touches[0].clientX;
    startOffset.current = offsetX;
  };

  const onTouchMove = (e: React.TouchEvent) => {
    if (!dragging.current || disabled) return;
    const delta = e.touches[0].clientX - startX.current;
    setOffsetX(clampOffset(startOffset.current + delta));
  };

  const onTouchEnd = (e: React.TouchEvent) => {
    finishDrag(e.changedTouches[0].clientX);
  };

  const onMouseDown = (e: React.MouseEvent) => {
    if (disabled) return;
    dragging.current = true;
    startX.current = e.clientX;
    startOffset.current = offsetX;
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging.current || disabled) return;
    const delta = e.clientX - startX.current;
    setOffsetX(clampOffset(startOffset.current + delta));
  };

  const onMouseUp = (e: React.MouseEvent) => {
    finishDrag(e.clientX);
  };

  return (
    <div className="relative overflow-hidden">
      <div className="absolute inset-y-0 right-0 flex w-[88px] items-center justify-center bg-red-600">
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            setOffsetX(0);
            onDeleteRequest();
          }}
          className="px-3 text-xs font-semibold text-white"
        >
          Удалить
        </button>
      </div>
      <div
        className="relative bg-white transition-transform duration-150 ease-out"
        style={{ transform: `translateX(${offsetX}px)` }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        {children}
      </div>
    </div>
  );
}
