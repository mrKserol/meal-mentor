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
      </div>
      <div className="relative z-10 flex w-full shrink-0 justify-center md:w-2/5">
        <div className="flex max-h-64 w-full max-w-[280px] items-center justify-center rounded-2xl bg-white/10 p-4 ring-4 ring-white/20 backdrop-blur-sm">
          <img
            src="/meal-mentor-mascot.png"
            alt="Meal Mentor — маскот приложения"
            className="max-h-56 w-auto object-contain drop-shadow-2xl"
            width={280}
            height={280}
            loading="lazy"
            decoding="async"
          />
        </div>
      </div>
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-primary-container/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-12 -left-8 h-40 w-40 rounded-full bg-primary-fixed/30 blur-2xl" />
    </section>
  );
}
