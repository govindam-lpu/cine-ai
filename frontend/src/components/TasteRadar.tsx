import type { Evidence } from "@/lib/api";

// Map the real evidence signals onto a pentagon. Each axis is 0..1 (0.5 = neutral / no signal).
function axesFrom(ev: Evidence) {
  const sig = (v: number | null, invert = false) =>
    v === null ? 0.5 : Math.max(0, Math.min(1, ((invert ? -v : v) + 1) / 2));
  const rated = ev.counts.rated || 1;
  const genreBreadth = ev.genre_affinity.filter((g) => g.n >= 2).length;
  return [
    { key: "obscure", label: "Obscure", value: sig(ev.obscurity_preference.value, true) },
    { key: "patient", label: "Patient", value: sig(ev.patience.value) },
    { key: "contrarian", label: "Contrarian", value: sig(ev.contrarianism.value, true) },
    { key: "rewatcher", label: "Rewatcher", value: Math.min(1, (ev.counts.rewatched / rated) * 4) },
    { key: "range", label: "Range", value: Math.min(1, genreBreadth / 8) },
  ];
}

function point(value: number, index: number, count: number, cx = 130, cy = 130, rmax = 96) {
  const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
  const r = 20 + value * (rmax - 20);
  return { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
}

export default function TasteRadar({ evidence }: { evidence: Evidence }) {
  const axes = axesFrom(evidence);
  const n = axes.length;
  const polygon = axes.map((a, i) => point(a.value, i, n)).map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  return (
    <svg viewBox="0 0 260 260" className="h-[260px] w-[260px]" role="img" aria-label="Taste radar">
      {[0.33, 0.66, 1].map((ring) => (
        <polygon
          key={ring}
          points={axes.map((_, i) => point(ring, i, n)).map((p) => `${p.x},${p.y}`).join(" ")}
          fill="none"
          stroke="var(--border-default)"
        />
      ))}
      {axes.map((a, i) => {
        const edge = point(1, i, n);
        const label = point(1.18, i, n);
        return (
          <g key={a.key}>
            <line x1={130} y1={130} x2={edge.x} y2={edge.y} stroke="var(--border-subtle)" />
            <text
              x={label.x}
              y={label.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-text-muted font-mono"
              fontSize="10"
            >
              {a.label}
            </text>
          </g>
        );
      })}
      <polygon points={polygon} fill="var(--accent-glow)" stroke="var(--accent)" strokeWidth="2" />
    </svg>
  );
}
