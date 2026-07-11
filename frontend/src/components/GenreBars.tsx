import type { GenreAffinity } from "@/lib/api";

// Genre affinity: bars relative to the personal baseline (positive = rates above, negative = below).
export default function GenreBars({ genres }: { genres: GenreAffinity[] }) {
  const withDelta = genres.filter((g) => g.delta !== null && g.n >= 2);
  const ranked = [...withDelta].sort((a, b) => (b.delta ?? 0) - (a.delta ?? 0)).slice(0, 8);
  if (ranked.length === 0) return null;
  const maxAbs = Math.max(0.5, ...ranked.map((g) => Math.abs(g.delta ?? 0)));

  return (
    <div className="space-y-2">
      {ranked.map((g) => {
        const delta = g.delta ?? 0;
        const width = (Math.abs(delta) / maxAbs) * 50; // % of half-width
        const positive = delta >= 0;
        return (
          <div key={g.genre} className="flex items-center gap-3 text-sm">
            <span className="w-28 shrink-0 truncate text-text-secondary">{g.genre}</span>
            <div className="relative h-3 flex-1 rounded-sm bg-[rgba(245,241,234,0.04)]">
              <div className="absolute left-1/2 top-0 h-full w-px bg-border-default" />
              <div
                className="absolute top-0 h-full rounded-sm"
                style={{
                  left: positive ? "50%" : `${50 - width}%`,
                  width: `${width}%`,
                  background: positive ? "var(--positive)" : "var(--negative)",
                }}
              />
            </div>
            <span className="w-10 shrink-0 text-right font-mono text-xs text-text-muted">
              {delta > 0 ? "+" : ""}
              {delta.toFixed(1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
