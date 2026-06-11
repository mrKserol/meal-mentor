import { DISCLAIMER_PARAGRAPHS } from "./disclaimerText";

interface DisclaimerTextBlockProps {
  className?: string;
}

export function DisclaimerTextBlock({ className = "" }: DisclaimerTextBlockProps) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 text-slate-800 shadow-sm ${className}`}>
      <div className="space-y-4 text-sm leading-6 sm:text-base sm:leading-7">
        {DISCLAIMER_PARAGRAPHS.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </section>
  );
}
