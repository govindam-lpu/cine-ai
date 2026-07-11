import type { TasteTimelineEntry } from "@/types/taste";

export default function TasteTimeline({ items }: { items: TasteTimelineEntry[] }) {
  return (
    <section className="panel space-y-4 p-6">
      <h3 className="font-display text-2xl text-text-primary">Taste evolution timeline</h3>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {items.map((item, index) => (
          <div key={item.label} className="border border-border-default p-4">
            <p className="font-mono text-xs text-accent">0{index + 1}</p>
            <h4 className="mt-3 font-display text-xl text-text-primary">{item.label}</h4>
            <p className="mt-2 text-sm text-text-secondary">{item.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
