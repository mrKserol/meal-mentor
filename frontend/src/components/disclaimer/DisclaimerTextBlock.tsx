import { DISCLAIMER_PARAGRAPHS, DISCLAIMER_TITLE } from "./disclaimerText";

interface DisclaimerTextBlockProps {
  className?: string;
}

export function DisclaimerTextBlock({ className = "" }: DisclaimerTextBlockProps) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 text-slate-800 shadow-sm ${className}`}>
      <h2 className="mb-4 text-xl font-bold tracking-tight text-slate-950">{DISCLAIMER_TITLE}</h2>
      <div className="space-y-4 text-sm leading-6 sm:text-base sm:leading-7">
        {DISCLAIMER_PARAGRAPHS.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </section>
  );
}
