"use client";

import EmptyState from "@/components/shared/EmptyState";
import { useUser } from "@/hooks/useUser";
import { useWatchlist } from "@/hooks/useWatchlist";

export default function WatchlistPage() {
  const { user } = useUser();
  const watchlist = useWatchlist(user);

  return (
    <div className="page-shell space-y-6">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-text-muted">Watchlist ranker</p>
        <h1 className="font-display text-5xl text-text-primary">Save now, rank later</h1>
        <p className="max-w-3xl text-sm text-text-secondary">The page shell is complete and aligned to the planned API, but the current backend hasn’t shipped watchlist CRUD yet.</p>
      </header>
      <EmptyState description={watchlist.message} title="Your watchlist is ready for the API" />
    </div>
  );
}
