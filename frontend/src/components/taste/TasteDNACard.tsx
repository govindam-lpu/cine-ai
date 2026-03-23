import type { DerivedTasteProfile } from "@/types/taste";
import type { UserProfile } from "@/types/user";

export default function TasteDNACard({ user, taste }: { user: UserProfile | null; taste: DerivedTasteProfile }) {
  return (
    <section className="panel space-y-6 border-border-accent bg-[linear-gradient(145deg,rgba(232,197,71,0.08),rgba(20,18,16,0.92))] p-6 md:p-8">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border-accent pb-4">
        <p className="font-display text-lg uppercase tracking-[0.28em] text-text-primary">Cinerex Taste DNA</p>
        <p className="text-sm text-text-secondary">@{user?.letterboxd_username ?? "guest"}</p>
      </div>
      <blockquote className="max-w-3xl font-display text-3xl italic leading-relaxed text-text-primary">
        “{taste.summary}”
      </blockquote>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Top genres</p>
          <p className="mt-2 text-sm text-text-secondary">{taste.top_genres.map((item) => item.genre).join(" · ")}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Favorite era</p>
          <p className="mt-2 text-sm text-text-secondary">{taste.preferred_eras[0]?.genre}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Pretension score</p>
          <p className="mt-2 text-sm text-text-secondary">{Math.round(taste.pretension_score * 100)}%</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Backend readiness</p>
          <p className="mt-2 text-sm text-text-secondary">{taste.backendReady ? "Taste endpoint live" : "Derived fallback mode"}</p>
        </div>
      </div>
    </section>
  );
}
