export default function CrewAffinities({ names }: { names: string[] }) {
  return (
    <section className="panel space-y-4 p-6">
      <h3 className="font-display text-2xl text-text-primary">Crew affinities</h3>
      <div className="flex flex-wrap gap-2">
        {names.map((name) => (
          <span key={name} className="border border-border-default px-3 py-2 text-sm text-text-secondary">{name}</span>
        ))}
      </div>
    </section>
  );
}
