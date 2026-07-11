"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { APIError, recommendationsApi } from "@/lib/api";
import type { Recommendation, RecommendationPayload } from "@/types/recommendation";
import type { UserProfile } from "@/types/user";

export function useRecommendations(user: UserProfile | null, mood = "") {
  const [payload, setPayload] = useState<RecommendationPayload | null>(null);
  const [loading, setLoading] = useState(Boolean(user));
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setPayload(null);
      setLoading(false);
      setError(null);
      return null;
    }

    setLoading(true);
    try {
      const data = await recommendationsApi.get(user.user_id, mood || undefined);
      setPayload(data);
      setError(null);
      return data;
    } catch (err) {
      setPayload(null);
      setError(err instanceof APIError ? err.message : "Could not load recommendations.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [mood, user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return useMemo(() => {
    const recommendations = payload?.recommendations ?? [];
    return {
      feature: recommendations[0] as Recommendation | undefined,
      grid: recommendations.slice(1, 4),
      rest: recommendations.slice(4),
      headerNote: payload
        ? `Ranked from ${payload.basis?.films_analyzed ?? recommendations.length} imported films and live TMDB results.`
        : "Recommendations will appear after your Letterboxd history is imported.",
      generatedAt: payload?.generated_at,
      basis: payload?.basis,
      loading,
      error,
      refresh
    };
  }, [error, loading, payload, refresh]);
}
