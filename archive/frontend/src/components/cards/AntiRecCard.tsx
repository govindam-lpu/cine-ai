import ConfidenceBadge from "@/components/recommendations/ConfidenceBadge";
import { getPosterUrl } from "@/lib/tmdb";
import type { AntiRecommendation } from "@/types/recommendation";

export default function AntiRecCard({ item }: { item: AntiRecommendation }) {
  const poster = getPosterUrl(item.film.poster_path);

  return (
    <article className="panel grid overflow-hidden border-[rgba(225,111,114,0.3)] bg-[rgba(225,111,114,0.05)] p-0 md:grid-cols-[120px_1fr]">
      <div className="bg-bg-elevated">
        {poster ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={item.film.title} className="h-full w-full object-cover" src={poster} />
        ) : null}
      </div>
      <div className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-negative">Likely poor fit</p>
            <h3 className="font-display text-2xl text-text-primary">{item.film.title}</h3>
          </div>
          <ConfidenceBadge confidence={item.confidence} />
        </div>
        <p className="text-sm text-text-secondary">{item.reason}</p>
      </div>
    </article>
  );
}
