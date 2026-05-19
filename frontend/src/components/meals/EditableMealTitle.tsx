import { useEffect, useRef, useState } from "react";

type EditableMealTitleProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export function EditableMealTitle({
  value,
  onChange,
  placeholder = "Приём пищи",
}: EditableMealTitleProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(value);
  }, [value, editing]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commit = () => {
    const next = draft.trim();
    onChange(next);
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          }
          if (e.key === "Escape") {
            setDraft(value);
            setEditing(false);
          }
        }}
        className="w-full rounded-lg border border-green-600 bg-white px-2 py-1.5 text-lg font-semibold text-slate-900 outline-none ring-2 ring-green-100"
        placeholder={placeholder}
      />
    );
  }

  const display = value.trim() || placeholder;

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="w-full rounded-lg px-1 py-0.5 text-left text-lg font-semibold leading-snug text-slate-900 transition hover:bg-slate-50"
      title="Нажмите, чтобы изменить название"
    >
      {display}
    </button>
  );
}
