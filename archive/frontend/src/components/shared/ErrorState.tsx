type ErrorStateProps = {
  title?: string;
  message: string;
};

export default function ErrorState({ title = "Something went wrong", message }: ErrorStateProps) {
  return (
    <section className="panel border border-negative/40 bg-[rgba(200,96,96,0.08)] p-6">
      <p className="text-xs uppercase tracking-[0.2em] text-negative">Error</p>
      <h2 className="mt-3 font-display text-2xl text-text-primary">{title}</h2>
      <p className="mt-2 text-sm text-text-secondary">{message}</p>
    </section>
  );
}
