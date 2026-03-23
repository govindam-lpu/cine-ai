"use client";

import { useMemo } from "react";

import type { AntiRecommendation, Recommendation } from "@/types/recommendation";
import type { UserProfile } from "@/types/user";

const seedRecommendations: Recommendation[] = [
  {
    film: {
      tmdb_id: 157336,
      media_type: "film",
      title: "Interstellar",
      release_year: 2014,
      runtime_minutes: 169,
      genres: ["Sci-Fi", "Drama"],
      directors: ["Christopher Nolan"],
      poster_path: "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
      tmdb_rating: 8.4,
      overview: "A team leaves Earth in search of a home for humanity."
    },
    reason: "A prestige-scale emotional sci-fi anchor that matches the editorial tone Cinerex is designed for.",
    confidence: "high",
    tags: ["epic", "emotional", "high-concept"],
    streaming: [{ provider_id: 8, provider_name: "Netflix" }],
    predicted_rating: 4.6
  },
  {
    film: {
      tmdb_id: 419430,
      media_type: "film",
      title: "Get Out",
      release_year: 2017,
      runtime_minutes: 104,
      genres: ["Horror", "Thriller"],
      directors: ["Jordan Peele"],
      poster_path: "/tFXcEccSQMf3lfhfXKSU9iRBpa3.jpg",
      tmdb_rating: 7.6,
      overview: "A visit with a girlfriend’s family reveals something far more sinister."
    },
    reason: "A strong balance of authorial voice and accessibility — ideal for the main recommendation grid.",
    confidence: "medium",
    tags: ["tense", "smart", "social satire"],
    streaming: [{ provider_id: 9, provider_name: "Prime Video" }],
    predicted_rating: 4.2
  },
  {
    film: {
      tmdb_id: 13,
      media_type: "film",
      title: "Forrest Gump",
      release_year: 1994,
      runtime_minutes: 142,
      genres: ["Drama", "Romance"],
      directors: ["Robert Zemeckis"],
      poster_path: "/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg",
      tmdb_rating: 8.5,
      overview: "A life story carried through modern American history."
    },
    reason: "A warm, emotionally direct pick that broadens the dashboard tone.",
    confidence: "medium",
    tags: ["comfort", "sweeping", "classic"],
    streaming: [{ provider_id: 15, provider_name: "Hulu" }],
    predicted_rating: 4.0
  },
  {
    film: {
      tmdb_id: 496243,
      media_type: "film",
      title: "Parasite",
      release_year: 2019,
      runtime_minutes: 133,
      genres: ["Thriller", "Drama"],
      directors: ["Bong Joon Ho"],
      poster_path: "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
      tmdb_rating: 8.5,
      overview: "A poor family infiltrates a wealthy household with escalating consequences."
    },
    reason: "Sharp, stylish, and deeply discussable — ideal for a prestige recommendation dashboard.",
    confidence: "high",
    tags: ["class satire", "thriller", "award-winning"],
    streaming: [{ provider_id: 337, provider_name: "Disney+" }],
    predicted_rating: 4.7
  },
  {
    film: {
      tmdb_id: 530385,
      media_type: "film",
      title: "Midsommar",
      release_year: 2019,
      runtime_minutes: 148,
      genres: ["Horror", "Drama"],
      directors: ["Ari Aster"],
      poster_path: "/7LEI8ulZzO5gy9Ww2NVCrKmHeDZ.jpg",
      tmdb_rating: 7.1,
      overview: "Grief and ritual collide in broad Scandinavian daylight."
    },
    reason: "This wild-card lane pushes the app toward more daring, atmosphere-first territory.",
    confidence: "wild",
    tags: ["disturbing", "auteur", "folk horror"],
    streaming: [{ provider_id: 384, provider_name: "HBO Max" }],
    predicted_rating: 3.9,
    is_wild_card: true
  }
];

const antiRecommendation: AntiRecommendation = {
  film: {
    tmdb_id: 86834,
    media_type: "film",
    title: "No Strings Attached",
    release_year: 2011,
    runtime_minutes: 108,
    genres: ["Romance", "Comedy"],
    poster_path: "/8sEL4RERUw4x0jD6caKQisRz6Lk.jpg",
    tmdb_rating: 6.3,
    overview: "A casual arrangement becomes unexpectedly complicated."
  },
  reason: "This is here as a design stand-in for anti-recommendations until the backend ships the real endpoint.",
  confidence: "medium"
};

export function useRecommendations(user: UserProfile | null) {
  return useMemo(() => {
    const headerNote = user?.sync_status === "complete"
      ? "Your account and sync are live. The recommendation engine endpoint is the next backend unlock, so this page currently uses editorial seed data to prove the complete UI."
      : "Connect and sync first. This page already supports the final layout, but the backend recommendation engine hasn’t landed yet.";

    return {
      feature: seedRecommendations[0],
      grid: seedRecommendations.slice(1, 4),
      wildCard: seedRecommendations[4],
      antiRecommendation,
      headerNote
    };
  }, [user]);
}
