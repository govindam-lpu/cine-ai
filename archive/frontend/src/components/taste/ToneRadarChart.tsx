import type { ToneProfile } from "@/types/taste";

const labels = [
  { key: "dark_light", label: "Dark ↔ Light" },
  { key: "slow_fast", label: "Slow ↔ Fast" },
  { key: "emotional_intellectual", label: "Emotional ↔ Intellectual" },
  { key: "arthouse_mainstream", label: "Arthouse ↔ Mainstream" }
] as const;

function point(value: number, index: number, radius = 86) {
  const angle = (Math.PI * 2 * index) / labels.length - Math.PI / 2;
  const normalized = (value + 1) / 2;
  const scaled = 36 + normalized * (radius - 36);
  return {
    x: 110 + Math.cos(angle) * scaled,
    y: 110 + Math.sin(angle) * scaled
  };
}

export default function ToneRadarChart({ tone }: { tone: ToneProfile }) {
  const values = labels.map(({ key }, index) => point(tone[key], index));
  const polygon = values.map(({ x, y }) => `${x},${y}`).join(" ");

  return (
    <div className="panel flex flex-col items-center gap-4 p-6">
      <h3 className="font-display text-2xl text-text-primary">Tone profile</h3>
      <svg className="h-[220px] w-[220px]" viewBox="0 0 220 220">
        {[40, 60, 80].map((radius) => (
          <circle key={radius} cx="110" cy="110" fill="none" r={radius} stroke="rgba(255,255,255,0.1)" />
        ))}
        {labels.map((_, index) => {
          const axis = point(1, index, 86);
          return <line key={index} stroke="rgba(255,255,255,0.1)" x1="110" x2={axis.x} y1="110" y2={axis.y} />;
        })}
        <polygon fill="rgba(232,197,71,0.18)" points={polygon} stroke="rgba(232,197,71,0.8)" strokeWidth="2" />
      </svg>
      <div className="grid w-full gap-2 text-sm text-text-secondary sm:grid-cols-2">
        {labels.map(({ key, label }) => (
          <div key={key} className="border border-border-default px-3 py-2">
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
