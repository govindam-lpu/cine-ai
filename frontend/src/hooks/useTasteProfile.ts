"use client";

import { useMemo } from "react";

import type { DerivedTasteProfile } from "@/types/taste";
import type { UserProfile } from "@/types/user";

function buildSummary(user: UserProfile | null) {
  if (!user) {
    return "Cinerex builds your taste portrait from what you actually watch, rate, and return to.";
  }

  const watchDepth =
    user.total_films_watched >= 150
      ? "a deep and consistent movie habit"
      : user.total_films_watched >= 30
        ? "the beginnings of a reliable viewing pattern"
        : "an early-stage profile that still needs more signal";

  const formatLine =
    user.preferred_format === "films"
      ? "You’re clearly film-first right now"
      : user.preferred_format === "shows"
        ? "Your long-form storytelling preference is noted, though TV sync is still Phase 2"
        : "You’re open to both films and shows, even though the current sync engine is still film-led";

  return `${watchDepth}. ${formatLine}. Once the backend exposes the full taste endpoint, this page can swap from inferred signals to generated analysis without changing the UI.`;
}

export function useTasteProfile(user: UserProfile | null) {
  return useMemo<DerivedTasteProfile>(() => {
    const baseValue = Math.max(user?.total_films_watched ?? 0, 12);
    const backendReady = Boolean(user?.has_taste_profile);

    return {
      summary: buildSummary(user),
      fingerprint: backendReady ? "AI profile ready" : "Derived from connected account + sync state",
      top_genres: [
        { genre: "Drama", value: Math.min(44, 18 + Math.round(baseValue / 6)) },
        { genre: "Thriller", value: 24 },
        { genre: "Sci‑Fi", value: 18 },
        { genre: "Romance", value: 14 }
      ],
      preferred_eras: [
        { genre: "1990s", value: 34 },
        { genre: "2000s", value: 29 },
        { genre: "2010s", value: 22 },
        { genre: "Classic", value: 15 }
      ],
      tone_profile: {
        dark_light: -0.32,
        slow_fast: -0.24,
        emotional_intellectual: 0.28,
        arthouse_mainstream: -0.12
      },
      invisible_preferences: [
        "You seem to favor atmosphere before plot momentum.",
        "Your current profile is strongest when a film has a distinct authorial point of view.",
        "A fuller sync will make pacing and decade preferences much more reliable."
      ],
      crew_affinities: ["Denis Villeneuve", "Sofia Coppola", "Roger Deakins", "Ludwig Göransson", "Greta Gerwig"],
      negative_signals: [
        "Broad comedic chaos does not appear to be the main draw of your current profile.",
        "Fast-cut spectacle may overperform less than mood-driven storytelling."
      ],
      emotional_aftertastes: [
        { genre: "Melancholy", value: 82 },
        { genre: "Awe", value: 74 },
        { genre: "Tension", value: 61 }
      ],
      pretension_score: 0.58,
      timeline: [
        { label: "Connect", description: "Letterboxd account linked and user profile created." },
        {
          label: "Sync",
          description:
            user?.sync_status === "complete"
              ? `History imported with ${user.total_films_watched} watched titles in the database.`
              : "Run the sync to unlock history-backed taste analysis."
        },
        {
          label: "Taste engine",
          description: backendReady
            ? "Backend taste profile is available."
            : "The dedicated /profile endpoint is still pending in the backend."
        },
        { label: "Recommendations", description: "Recommendation UI is ready to receive the real backend payload once that endpoint lands." }
      ],
      backendReady
    };
  }, [user]);
}
