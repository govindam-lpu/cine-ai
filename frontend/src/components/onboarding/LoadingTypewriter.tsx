import { Check, Circle } from "lucide-react";

import type { ScrapeJob } from "@/types/user";

const steps = ["Fetch Letterboxd", "Match metadata", "Store history", "Open workspace"];

export default function LoadingTypewriter({ job }: { job: ScrapeJob | null }) {
  const processed = job?.progress.films_processed ?? 0;
  const total = job?.progress.films_total ?? 0;
  const percent = total ? Math.min(100, Math.round((processed / total) * 100)) : 8;

  return (
    <section className="panel space-y-6 p-6 md:p-8">
      <div>
        <p className="eyebrow">Step 2 / Sync</p>
        <h2 className="mt-2 font-display text-4xl text-text-primary">Building your profile</h2>
      </div>
      <div className="h-2 overflow-hidden rounded-[999px] bg-[rgba(245,241,234,0.08)]">
        <div className="h-full rounded-[999px] bg-accent transition-all duration-300" style={{ width: `${percent}%` }} />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        {steps.map((step, index) => {
          const complete = job?.status === "complete" || index < (job?.status === "enriching" ? 2 : job?.status === "scraping" ? 1 : 0);
          const Icon = complete ? Check : Circle;
          return (
            <div key={step} className="stat-card">
              <Icon className={complete ? "text-accent" : "text-text-muted"} size={18} />
              <p className="mt-3 text-sm text-text-primary">{step}</p>
            </div>
          );
        })}
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="stat-card">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Status</p>
          <p className="mt-2 text-lg capitalize text-text-primary">{job?.status ?? "Waiting"}</p>
        </div>
        <div className="stat-card">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Current step</p>
          <p className="mt-2 text-lg text-text-primary">{job?.progress.step ?? "Queued"}</p>
        </div>
        <div className="stat-card">
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Films processed</p>
          <p className="mt-2 text-lg text-text-primary">{processed} / {total}</p>
        </div>
      </div>
    </section>
  );
}
