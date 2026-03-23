"use client";

import { useMemo } from "react";

import type { UserProfile } from "@/types/user";

export function useWatchlist(user: UserProfile | null) {
  return useMemo(
    () => ({
      total: 0,
      items: [] as never[],
      message: user
        ? "The backend watchlist endpoints are scaffolded but not implemented yet, so this page is ready for the API shape but currently empty."
        : "Create a profile first to unlock your personal watchlist workspace."
    }),
    [user]
  );
}
