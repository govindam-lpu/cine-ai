import { percentage } from "@/lib/utils";
import type { GenreStat } from "@/types/taste";

export default function GenreBreakdown({ items, title }: { items: GenreStat[]; title: string }) {
  return (
    <section className="panel space-y-4 p-6">
      <h3 className="font-display text-2xl text-text-primary">{title}</h3>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.genre} className="space-y-2">
            <div className="flex items-center justify-between text-sm text-text-secondary">
              <span>{item.genre}</span>
              <span>{percentage(item.value)}</span>
            </div>
            <div className="h-2 bg-bg-elevated">
              <div className="h-2 bg-accent" style={{ width: `${item.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
