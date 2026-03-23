import FilmCardCompact from "@/components/cards/FilmCardCompact";
import FilmCardFeature from "@/components/cards/FilmCardFeature";
import type { Recommendation } from "@/types/recommendation";

export default function RecommendationGrid({ feature, items }: { feature: Recommendation; items: Recommendation[] }) {
  return (
    <section className="space-y-6">
      <FilmCardFeature item={feature} />
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <FilmCardCompact key={item.film.tmdb_id} item={item} />
        ))}
      </div>
    </section>
  );
}
