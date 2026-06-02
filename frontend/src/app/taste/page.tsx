"use client";

import EmptyState from "@/components/shared/EmptyState";
import ErrorState from "@/components/shared/ErrorState";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import GenreBreakdown from "@/components/taste/GenreBreakdown";
import CrewAffinities from "@/components/taste/CrewAffinities";
import PretensionScore from "@/components/taste/PretensionScore";
import TasteDNACard from "@/components/taste/TasteDNACard";
import TasteTimeline from "@/components/taste/TasteTimeline";
import ToneRadarChart from "@/components/taste/ToneRadarChart";
import { useTasteProfile } from "@/hooks/useTasteProfile";
import { useUser } from "@/hooks/useUser";

export default function TastePage() {
  const { user, loading: userLoading, error: userError } = useUser();
  const { taste, loading: tasteLoading, error: tasteError } = useTasteProfile(user);

  if (userLoading) {
    return <div className="page-shell"><LoadingSpinner label="Loading profile..." /></div>;
  }

  if (userError) {
    return <div className="page-shell"><ErrorState message={userError} /></div>;
  }

  if (!user) {
    return <div className="page-shell"><EmptyState actionHref="/" actionLabel="Start onboarding" description="Link a Letterboxd profile first so Cinerex has something to analyze." title="No Taste DNA yet" /></div>;
  }

  if (tasteLoading) {
    return <div className="page-shell"><LoadingSpinner label="Analyzing imported films..." /></div>;
  }

  if (tasteError || !taste) {
    return <div className="page-shell"><ErrorState message={tasteError ?? "Taste profile is not ready yet."} title="Taste profile unavailable" /></div>;
  }

  return (
    <div className="page-shell space-y-8">
      <header className="space-y-3">
        <p className="eyebrow">Taste DNA</p>
        <h1 className="font-display text-5xl text-text-primary">The full profile view</h1>
        <p className="max-w-4xl text-sm text-text-secondary">Built from your imported Letterboxd watch history and TMDB metadata. No browser-side placeholder taste values.</p>
      </header>
      <TasteDNACard taste={taste} user={user} />
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ToneRadarChart tone={taste.tone_profile} />
        <PretensionScore value={taste.pretension_score} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <GenreBreakdown items={taste.top_genres} title="Genre breakdown" />
        <GenreBreakdown items={taste.preferred_eras} title="Preferred eras" />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <CrewAffinities names={taste.crew_affinities} />
        <section className="panel space-y-4 p-6">
          <h3 className="font-display text-2xl text-text-primary">Invisible preferences</h3>
          <div className="space-y-3">
            {taste.invisible_preferences.map((item) => (
              <div key={item} className="border border-border-default p-4 text-sm text-text-secondary">{item}</div>
            ))}
          </div>
        </section>
      </div>
      <TasteTimeline items={taste.timeline} />
    </div>
  );
}
