import type { DerivedTasteProfile } from "@/types/taste";
import type { UserProfile } from "@/types/user";

export default function TasteDNACard({ user, taste }: { user: UserProfile | null; taste: DerivedTasteProfile }) {
  return (
    <section className="panel overflow-hidden border-border-accent p-0">
      <div className="border-b border-border-accent bg-[rgba(243,201,79,0.07)] p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="eyebrow">Taste DNA</p>
            <h2 className="mt-2 font-display text-3xl text-text-primary">@{user?.letterboxd_username ?? "guest"}</h2>
          </div>
          <span className="rounded-[999px] border border-border-accent px-3 py-1 text-xs uppercase tracking-[0.14em] text-accent">
            {taste.backendReady ? "Live profile" : "Preview mode"}
          </span>
        </div>
      </div>
      <div className="space-y-6 p-5 md:p-6">
        <p className="max-w-3xl text-lg leading-8 text-text-primary">{taste.summary}</p>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {[
            ["Top genres", taste.top_genres.map((item) => item.genre).join(" / ")],
            ["Favorite era", taste.preferred_eras[0]?.genre ?? "Learning"],
            ["Pretension score", `${Math.round(taste.pretension_score * 100)}%`],
            ["Readiness", taste.backendReady ? "Taste endpoint live" : "Derived fallback"]
          ].map(([label, value]) => (
            <div key={label} className="stat-card">
              <p className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{label}</p>
              <p className="mt-2 text-sm text-text-secondary">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
