import ConfidenceBadge from "@/components/recommendations/ConfidenceBadge";
import StreamingBadge from "@/components/recommendations/StreamingBadge";
import { getPosterUrl } from "@/lib/tmdb";
import { formatRuntime } from "@/lib/utils";
import type { Recommendation } from "@/types/recommendation";

export default function FilmCardFeature({ item }: { item: Recommendation }) {
  const poster = getPosterUrl(item.film.poster_path);

  return (
    <article className="panel grid overflow-hidden border-border-accent p-0 md:grid-cols-[260px_1fr]">
      <div className="min-h-[360px] bg-bg-elevated">
        {poster ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={item.film.title} className="h-full w-full object-cover" src={poster} />
        ) : (
          <div className="flex h-full items-center justify-center bg-bg-elevated text-text-muted">No poster</div>
        )}
      </div>
      <div className="space-y-6 p-6 md:p-8">
        <div className="flex flex-wrap items-center gap-3">
          <p className="eyebrow">Top pick</p>
          <ConfidenceBadge confidence={item.confidence} />
        </div>
        <div className="space-y-2">
          <h2 className="font-display text-5xl leading-tight text-text-primary">{item.film.title}</h2>
          <p className="text-sm text-text-secondary">
            {item.film.release_year} / {item.film.genres.join(" / ")} / {formatRuntime(item.film.runtime_minutes)}
          </p>
          <p className="font-mono text-base text-accent">Predicted fit: {item.predicted_rating.toFixed(1)} / 5</p>
        </div>
        <p className="max-w-3xl text-base text-text-secondary">{item.reason}</p>
        <p className="text-sm text-text-muted">{item.film.overview}</p>
        <div className="flex flex-wrap gap-2">
          {item.tags.map((tag) => (
            <span key={tag} className="rounded-[999px] border border-border-default bg-[rgba(245,241,234,0.03)] px-3 py-1 text-xs text-text-secondary">
              {tag}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {item.streaming.map((option) => (
            <StreamingBadge key={`${item.film.tmdb_id}-${option.provider_id}`} option={option} />
          ))}
        </div>
      </div>
    </article>
  );
}
