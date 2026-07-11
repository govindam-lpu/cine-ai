import type { Recommendation } from "@/lib/api";
import { posterUrl } from "@/lib/api";

// The reason IS the card — not a caption under a poster. That's the product.
export default function RecommendationCard({ rec }: { rec: Recommendation }) {
  const poster = posterUrl(rec.poster_path);
  const chips = rec.signals.filter((s) => s.factor !== "similarity").slice(0, 3);

  return (
    <article className="panel grid overflow-hidden sm:grid-cols-[120px_1fr]">
      <div className="hidden bg-bg-elevated sm:block">
        {poster ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={rec.title} className="h-full w-full object-cover" src={poster} />
        ) : (
          <div className="flex h-full min-h-[180px] items-center justify-center text-xs text-text-muted">
            No poster
          </div>
        )}
      </div>
      <div className="space-y-3 p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="font-display text-xl text-text-primary">
            {rec.title}
            {rec.year ? <span className="ml-2 text-base text-text-muted">{rec.year}</span> : null}
          </h3>
        </div>
        <p className="text-[0.95rem] leading-relaxed text-text-primary">{rec.reason}</p>
        {chips.length > 0 ? (
          <div className="flex flex-wrap gap-2 pt-1">
            {chips.map((s, i) => (
              <span
                key={i}
                className="rounded-full border border-border-subtle px-2.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-text-muted"
              >
                {s.name ?? s.factor}
              </span>
            ))}
          </div>
        ) : null}
        {rec.at_capacity ? (
          <p className="font-mono text-[0.65rem] text-warning">written from your signals · AI paused</p>
        ) : null}
      </div>
    </article>
  );
}
