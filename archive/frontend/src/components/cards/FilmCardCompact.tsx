import ConfidenceBadge from "@/components/recommendations/ConfidenceBadge";
import StreamingBadge from "@/components/recommendations/StreamingBadge";
import { getPosterUrl } from "@/lib/tmdb";
import { formatRuntime } from "@/lib/utils";
import type { Recommendation } from "@/types/recommendation";

export default function FilmCardCompact({ item }: { item: Recommendation }) {
  const poster = getPosterUrl(item.film.poster_path);

  return (
    <article className="panel group overflow-hidden p-0 transition duration-200 hover:-translate-y-1 hover:border-border-accent">
      <div className="aspect-[2/3] w-full bg-bg-elevated">
        {poster ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={item.film.title} className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]" src={poster} />
        ) : (
          <div className="flex h-full items-center justify-center bg-bg-elevated text-text-muted">No poster</div>
        )}
      </div>
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-2xl leading-tight text-text-primary">{item.film.title}</h3>
            <p className="text-xs text-text-secondary">
              {item.film.release_year} / {item.film.genres.slice(0, 2).join(" / ")} / {formatRuntime(item.film.runtime_minutes)}
            </p>
          </div>
          <ConfidenceBadge confidence={item.confidence} />
        </div>
        <p className="font-mono text-sm text-accent">{item.predicted_rating.toFixed(1)} / 5 fit</p>
        <p className="text-sm text-text-secondary">{item.reason}</p>
        <div className="flex flex-wrap gap-2">
          {item.streaming.map((option) => (
            <StreamingBadge key={`${item.film.tmdb_id}-${option.provider_id}`} option={option} />
          ))}
        </div>
      </div>
    </article>
  );
}
