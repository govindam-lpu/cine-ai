"use client";

import { useCallback, useEffect, useState } from "react";

import { APIError, profileApi } from "@/lib/api";
import type { DerivedTasteProfile } from "@/types/taste";
import type { UserProfile } from "@/types/user";

export function useTasteProfile(user: UserProfile | null) {
  const [taste, setTaste] = useState<DerivedTasteProfile | null>(null);
  const [loading, setLoading] = useState(Boolean(user));
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setTaste(null);
      setLoading(false);
      setError(null);
      return null;
    }

    setLoading(true);
    try {
      const profile = await profileApi.get(user.user_id);
      setTaste({ ...profile, backendReady: true });
      setError(null);
      return profile;
    } catch (err) {
      const message = err instanceof APIError ? err.message : "Could not load the taste profile.";
      setTaste(null);
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { taste, loading, error, refresh };
}
