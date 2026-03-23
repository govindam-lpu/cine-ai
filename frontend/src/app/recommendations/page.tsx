"use client";

import { useState } from "react";

import AntiRecCard from "@/components/cards/AntiRecCard";
import EmptyState from "@/components/shared/EmptyState";
import ErrorState from "@/components/shared/ErrorState";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import FilterSidebar from "@/components/recommendations/FilterSidebar";
import MoodSelector from "@/components/recommendations/MoodSelector";
import RecommendationGrid from "@/components/recommendations/RecommendationGrid";
import WildCardCard from "@/components/recommendations/WildCardCard";
import TasteDNACard from "@/components/taste/TasteDNACard";
import { useRecommendations } from "@/hooks/useRecommendations";
import { useTasteProfile } from "@/hooks/useTasteProfile";
import { useUser } from "@/hooks/useUser";
import { formatDate } from "@/lib/utils";

export default function RecommendationsPage() {
  const { user, loading, error } = useUser();
  const taste = useTasteProfile(user);
  const recs = useRecommendations(user);
  const [mood, setMood] = useState("");

  if (loading) return <div className="page-shell"><LoadingSpinner label="Loading your dashboard…" /></div>;
  if (error) return <div className="page-shell"><ErrorState message={error} /></div>;
  if (!user) return <div className="page-shell"><EmptyState actionHref="/" actionLabel="Create profile" description="Connect a Letterboxd account first so Cinerex has a user to work with." title="No active profile" /></div>;

  return (
    <div className="page-shell space-y-8">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-text-muted">Recommendations</p>
        <h1 className="font-display text-5xl text-text-primary">Your recommendation dashboard</h1>
        <p className="max-w-4xl text-sm text-text-secondary">{recs.headerNote}</p>
      </header>

      <section className="grid gap-6 xl:grid-cols-[280px_1fr]">
        <div className="space-y-6">
          <TasteDNACard taste={taste} user={user} />
          <FilterSidebar mood={mood} setMood={setMood} user={user} />
        </div>
        <div className="space-y-6">
          <MoodSelector onChange={setMood} value={mood} />
          <section className="grid gap-4 sm:grid-cols-3">
            <div className="panel p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Sync status</p>
              <p className="mt-2 text-2xl text-text-primary">{user.sync_status}</p>
            </div>
            <div className="panel p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Films watched</p>
              <p className="mt-2 text-2xl text-text-primary">{user.total_films_watched}</p>
            </div>
            <div className="panel p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Last synced</p>
              <p className="mt-2 text-sm text-text-primary">{formatDate(user.last_synced_at)}</p>
            </div>
          </section>
          <RecommendationGrid feature={recs.feature} items={recs.grid} />
          <WildCardCard item={recs.wildCard} />
          <AntiRecCard item={recs.antiRecommendation} />
        </div>
      </section>
    </div>
  );
}
