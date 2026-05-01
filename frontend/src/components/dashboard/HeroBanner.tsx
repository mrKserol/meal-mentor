interface HeroBannerProps {
  greetingName: string;
  subtitleLine: string;
}

export function HeroBanner({ greetingName, subtitleLine }: HeroBannerProps) {
  return (
    <section className="relative flex min-h-[260px] flex-col items-center justify-between gap-8 overflow-hidden rounded-xl bg-gradient-to-br from-primary to-primary-fixed-dim px-6 py-8 text-white shadow-md md:flex-row md:items-center md:px-10">
      <div className="relative z-10 w-full space-y-4 md:w-3/5">
        <span className="inline-block rounded-full bg-white/20 px-3 py-1 font-label-sm text-label-sm text-white backdrop-blur-sm">
          Welcome back, {greetingName}!
        </span>
        <h2 className="font-h1 text-h1 leading-tight text-white">Цели на сегодня</h2>
        <p className="max-w-xl font-body-md text-body-md text-white/95">{subtitleLine}</p>
        <div className="flex flex-wrap gap-3 pt-2">
          <button
            type="button"
            disabled
            title="Скоро"
            className="cursor-not-allowed rounded-lg bg-white/90 px-5 py-2.5 text-sm font-bold text-primary opacity-70"
          >
            Запланировать обед
          </button>
          <button
            type="button"
            disabled
            title="Скоро"
            className="cursor-not-allowed rounded-lg border border-white/40 bg-white/10 px-5 py-2.5 text-sm font-bold text-white opacity-70"
          >
            Аналитика
          </button>
        </div>
      </div>
      <div className="relative z-10 flex w-full shrink-0 justify-center md:w-2/5">
        <div
          className="flex h-48 w-48 items-center justify-center rounded-3xl bg-white/10 ring-4 ring-white/20 backdrop-blur-sm"
          aria-hidden
        >
          <svg viewBox="0 0 120 120" className="h-28 w-28 text-white/95" aria-hidden>
            <circle cx="60" cy="60" r="44" fill="none" stroke="currentColor" strokeWidth="4" opacity="0.35" />
            <path d="M40 72 Q60 42 80 72" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
            <circle cx="48" cy="52" r="5" fill="currentColor" />
            <circle cx="72" cy="52" r="5" fill="currentColor" />
          </svg>
        </div>
      </div>
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-primary-container/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-12 -left-8 h-40 w-40 rounded-full bg-primary-fixed/30 blur-2xl" />
    </section>
  );
}
