import type { Recommendation } from "@/lib/api";
import { letterboxdUrl, posterUrl } from "@/lib/api";

// The reason IS the card — not a caption under a poster. Numbered like a catalogue entry.
export default function RecommendationCard({ rec, index }: { rec: Recommendation; index?: number }) {
  const poster = posterUrl(rec.poster_path);
  const chips = rec.signals.filter((s) => s.factor !== "similarity").slice(0, 3);

  return (
    <article className="panel grid overflow-hidden sm:grid-cols-[110px_1fr]">
      <div className="hidden border-r border-border-subtle bg-bg-elevated sm:block">
        {poster ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={rec.title} className="h-full w-full object-cover" src={poster} />
        ) : (
          <div className="flex h-full min-h-[170px] items-center justify-center text-xs text-text-muted">
            No poster
          </div>
        )}
      </div>
      <div className="space-y-3 p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="font-display text-xl leading-tight text-text-primary">
            {rec.title}
            {rec.year ? <span className="ml-2 text-base font-normal text-text-muted">{rec.year}</span> : null}
          </h3>
          {index != null ? (
            <span className="shrink-0 font-mono text-xs text-text-muted">
              {String(index).padStart(2, "0")}
            </span>
          ) : null}
        </div>
        <p className="text-[0.98rem] leading-relaxed text-text-primary">{rec.reason}</p>
        {chips.length > 0 ? (
          <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1">
            {chips.map((s, i) => (
              <span key={i} className="font-mono text-[0.65rem] uppercase tracking-wide text-accent">
                {s.name ?? s.factor}
              </span>
            ))}
          </div>
        ) : null}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle pt-3">
          {rec.tmdb_rating ? (
            <span className="font-mono text-[0.7rem] text-text-secondary" title="TMDB community average">
              ★ {rec.tmdb_rating.toFixed(1)}
              <span className="text-text-muted"> /10 · TMDB</span>
            </span>
          ) : (
            <span />
          )}
          <a
            href={letterboxdUrl(rec.tmdb_id)}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[0.7rem] uppercase tracking-wide text-accent hover:underline"
          >
            View on Letterboxd ↗
          </a>
        </div>
        {rec.at_capacity ? (
          <p className="font-mono text-[0.65rem] text-warning">written from your signals · AI paused</p>
        ) : null}
      </div>
    </article>
  );
}
