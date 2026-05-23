interface HeroBannerProps {
  greetingName: string;
  subtitleLine: string;
}

export function HeroBanner({ greetingName, subtitleLine }: HeroBannerProps) {
  return (
    <section className="relative flex items-center justify-between gap-4 overflow-hidden rounded-xl bg-gradient-to-br from-primary to-primary-fixed-dim px-5 py-6 text-white shadow-md sm:px-7 md:px-10">
      <div className="relative z-10 min-w-0 flex-1 space-y-3">
        <span className="inline-block rounded-full bg-white/20 px-3 py-1 font-label-sm text-label-sm text-white backdrop-blur-sm">
          Welcome back, {greetingName}!
        </span>
        <h2 className="text-lg font-bold leading-tight text-white sm:font-h1 sm:text-h1">
          Питание на сегодня
        </h2>
        <p className="max-w-xl font-body-md text-body-md text-white/95">{subtitleLine}</p>
      </div>
      <div className="relative z-10 flex shrink-0 items-center justify-end">
        <img
          src="/meal-mentor-mascot.png"
          alt="Meal Mentor — маскот приложения"
          className="h-[7.5rem] w-auto object-contain drop-shadow-xl sm:h-24 md:h-28"
          width={168}
          height={168}
          loading="lazy"
          decoding="async"
        />
      </div>
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-primary-container/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-12 -left-8 h-40 w-40 rounded-full bg-primary-fixed/30 blur-2xl" />
    </section>
  );
}
