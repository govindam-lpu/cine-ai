import type { Evidence } from "@/lib/api";
import GenreBars from "@/components/GenreBars";
import TasteRadar from "@/components/TasteRadar";

function interpret(value: number | null, pos: string, neg: string, mid = "mixed"): string {
  if (value === null) return mid;
  if (value >= 0.25) return pos;
  if (value <= -0.25) return neg;
  return mid;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card">
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-text-muted">{label}</p>
      <p className="mt-1 text-sm text-text-primary">{value}</p>
    </div>
  );
}

export default function TasteDNACard({
  summary,
  evidence,
  displayName,
  handle,
}: {
  summary: string | null;
  evidence: Evidence;
  displayName: string | null;
  handle: string;
}) {
  const ev = evidence;
  const directors = ev.crew_affinity.director.slice(0, 4);

  return (
    <section className="panel space-y-8 p-6 md:p-8">
      <div className="space-y-2">
        <p className="eyebrow">Taste DNA</p>
        <h1 className="font-display text-3xl text-text-primary md:text-4xl">
          {displayName || handle}
        </h1>
      </div>

      {summary ? (
        <p className="max-w-3xl font-display text-2xl leading-relaxed text-text-primary md:text-[1.7rem]">
          {summary}
        </p>
      ) : null}

      <div className="grid gap-8 lg:grid-cols-[280px_1fr] lg:items-start">
        <div className="flex justify-center">
          <TasteRadar evidence={ev} />
        </div>
        <div className="space-y-6">
          <div>
            <p className="mb-3 font-mono text-xs uppercase tracking-[0.14em] text-text-muted">
              Genres vs your baseline
            </p>
            <GenreBars genres={ev.genre_affinity} />
          </div>
          {directors.length > 0 ? (
            <div>
              <p className="mb-2 font-mono text-xs uppercase tracking-[0.14em] text-text-muted">
                Directors you rate up
              </p>
              <div className="flex flex-wrap gap-2">
                {directors.map((d) => (
                  <span
                    key={d.name}
                    className="rounded-full border border-border-default px-3 py-1 text-sm text-text-secondary"
                  >
                    {d.name} <span className="text-text-muted">×{d.n}</span>
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Films rated"
          value={`${ev.counts.rated} of ${ev.counts.films}`}
        />
        <Stat
          label="Consensus"
          value={interpret(ev.contrarianism.value, "agrees with critics", "goes against the grain")}
        />
        <Stat
          label="Popularity"
          value={interpret(ev.obscurity_preference.value, "likes the popular", "seeks the obscure")}
        />
        <Stat
          label="Patience"
          value={interpret(ev.patience.value, "rewards the long", "prefers the tight")}
        />
      </div>
    </section>
  );
}
