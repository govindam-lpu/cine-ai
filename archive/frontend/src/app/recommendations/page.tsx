"use client";

import { useState } from "react";
import { CalendarClock, Clapperboard, RefreshCcw } from "lucide-react";

import EmptyState from "@/components/shared/EmptyState";
import ErrorState from "@/components/shared/ErrorState";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import MoodSelector from "@/components/recommendations/MoodSelector";
import RecommendationGrid from "@/components/recommendations/RecommendationGrid";
import TasteDNACard from "@/components/taste/TasteDNACard";
import { useRecommendations } from "@/hooks/useRecommendations";
import { useTasteProfile } from "@/hooks/useTasteProfile";
import { useUser } from "@/hooks/useUser";
import { formatDate } from "@/lib/utils";

export default function RecommendationsPage() {
  const { user, loading, error } = useUser();
  const [mood, setMood] = useState("");
  const { taste, loading: tasteLoading, error: tasteError } = useTasteProfile(user);
  const recs = useRecommendations(user, mood);

  if (loading) return <div className="page-shell"><LoadingSpinner label="Loading your dashboard…" /></div>;
  if (error) return <div className="page-shell"><ErrorState message={error} /></div>;
  if (!user) return <div className="page-shell"><EmptyState actionHref="/" actionLabel="Create profile" description="Connect a Letterboxd account first so Cinerex has a user to work with." title="No active profile" /></div>;

  return (
    <div className="page-shell space-y-8">
      <header className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
        <div className="space-y-4">
          <p className="eyebrow">Recommendations</p>
          <h1 className="font-display text-5xl leading-tight text-text-primary md:text-6xl">Tonight's shortlist</h1>
          <p className="max-w-3xl text-base text-text-secondary">{recs.headerNote}</p>
        </div>
        <div className="panel grid gap-3 p-4">
          {[
            [RefreshCcw, "Sync", user.sync_status],
            [Clapperboard, "Watched", `${user.total_films_watched} films`],
            [CalendarClock, "Updated", formatDate(user.last_synced_at)]
          ].map(([Icon, label, value]) => (
            <div key={label as string} className="flex items-center gap-3 rounded-[6px] border border-border-default bg-[rgba(245,241,234,0.03)] p-3">
              <span className="text-accent"><Icon size={18} /></span>
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{label as string}</p>
                <p className="text-sm capitalize text-text-primary">{value as string}</p>
              </div>
            </div>
          ))}
        </div>
      </header>

      <section className="grid gap-6 xl:grid-cols-[280px_1fr]">
        <div className="space-y-6">
          {tasteLoading ? <LoadingSpinner label="Loading taste profile..." /> : null}
          {tasteError ? <ErrorState message={tasteError} title="Taste profile unavailable" /> : null}
          {taste ? <TasteDNACard taste={taste} user={user} /> : null}
        </div>
        <div className="space-y-6">
          <MoodSelector onChange={setMood} value={mood} />
          {recs.loading ? <LoadingSpinner label="Ranking TMDB candidates..." /> : null}
          {recs.error ? <ErrorState message={recs.error} title="Recommendations unavailable" /> : null}
          {!recs.loading && !recs.error && !recs.feature ? <EmptyState description="Import at least 10 films before recommendations can be ranked." title="No ranked picks yet" /> : null}
          {recs.feature ? <RecommendationGrid feature={recs.feature} items={recs.grid} /> : null}
        </div>
      </section>
    </div>
  );
}
