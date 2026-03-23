export default function PretensionScore({ value }: { value: number }) {
  const percentage = Math.round(value * 100);
  return (
    <section className="panel space-y-4 p-6">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Pretension score</p>
        <h3 className="mt-2 font-display text-2xl text-text-primary">Independent ↔ Populist</h3>
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-bg-elevated">
          <div className="h-3 bg-accent" style={{ width: `${percentage}%` }} />
        </div>
        <p className="text-sm text-text-secondary">{percentage}% of the way toward the more rarefied, auteur-heavy end of the spectrum.</p>
      </div>
    </section>
  );
}
