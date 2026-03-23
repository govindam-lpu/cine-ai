import ConfidenceBadge from "@/components/recommendations/ConfidenceBadge";
import type { Recommendation } from "@/types/recommendation";

export default function WildCardCard({ item }: { item: Recommendation }) {
  return (
    <article className="panel border-dashed border-accent bg-[rgba(232,197,71,0.04)] p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-accent">This week’s wild card</p>
          <h3 className="mt-2 font-display text-3xl text-text-primary">{item.film.title}</h3>
        </div>
        <ConfidenceBadge confidence="wild" />
      </div>
      <p className="mt-4 text-sm text-text-secondary">{item.reason}</p>
    </article>
  );
}
