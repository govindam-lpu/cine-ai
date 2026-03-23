import type { ScrapeJob } from "@/types/user";

const steps = [
  "Fetching your Letterboxd history",
  "Enriching with film metadata",
  "Identifying taste patterns",
  "Building your profile"
];

export default function LoadingTypewriter({ job }: { job: ScrapeJob | null }) {
  const activeStep = job?.progress.step?.toLowerCase() ?? "";

  return (
    <section className="panel space-y-6 p-6 md:p-8">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Step 2 · Loading</p>
        <h2 className="mt-2 font-display text-3xl text-text-primary">We’re building your profile</h2>
      </div>
      <div className="space-y-4">
        {steps.map((step, index) => {
          const complete = job?.status === "complete" || index < 1 || activeStep.includes(step.split(" ")[0].toLowerCase());
          const active = !complete && index === 2;
          return (
            <div key={step} className="flex items-center justify-between border-b border-border-default pb-3">
              <span className="text-base text-text-secondary">{step}…</span>
              <span className={active ? "animate-pulse text-accent" : complete ? "text-accent" : "text-text-muted"}>{complete ? "✓" : "●"}</span>
            </div>
          );
        })}
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="border border-border-default p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Status</p>
          <p className="mt-2 text-lg text-text-primary">{job?.status ?? "Waiting to start"}</p>
        </div>
        <div className="border border-border-default p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Current step</p>
          <p className="mt-2 text-lg text-text-primary">{job?.progress.step ?? "Queued"}</p>
        </div>
        <div className="border border-border-default p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Films processed</p>
          <p className="mt-2 text-lg text-text-primary">{job?.progress.films_processed ?? 0} / {job?.progress.films_total ?? 0}</p>
        </div>
      </div>
    </section>
  );
}
