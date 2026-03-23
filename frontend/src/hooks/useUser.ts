"use client";

import { useCallback, useEffect, useState } from "react";

import { APIError, usersApi } from "@/lib/api";
import { useUserStore } from "@/stores/userStore";
import type { UserProfile } from "@/types/user";

export function useUser(explicitUserId?: string | null) {
  const { userId: storedUserId, user, setUser } = useUserStore();
  const userId = explicitUserId ?? storedUserId;
  const [loading, setLoading] = useState(Boolean(userId));
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!userId) {
      setLoading(false);
      return null;
    }

    setLoading(true);
    try {
      const nextUser = await usersApi.get(userId);
      setUser(nextUser);
      setError(null);
      return nextUser;
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load your profile.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [setUser, userId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    user: user as UserProfile | null,
    userId,
    loading,
    error,
    refresh
  };
}
