"use client";

import { useEffect, useState } from "react";

import EmptyState from "@/components/shared/EmptyState";
import ErrorState from "@/components/shared/ErrorState";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { healthApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useUser } from "@/hooks/useUser";
import type { HealthPayload } from "@/types/user";

export default function SettingsPage() {
  const { user, loading, error } = useUser();
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    void healthApi
      .get()
      .then(setHealth)
      .catch((err: Error) => setHealthError(err.message));
  }, []);

  if (loading) return <div className="page-shell"><LoadingSpinner label="Loading settings…" /></div>;
  if (error) return <div className="page-shell"><ErrorState message={error} /></div>;
  if (!user) return <div className="page-shell"><EmptyState actionHref="/" actionLabel="Create profile" description="Create a profile before viewing account settings." title="No active user" /></div>;

  return (
    <div className="page-shell space-y-8">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-text-muted">Settings</p>
        <h1 className="font-display text-5xl text-text-primary">Profile + backend status</h1>
        <p className="max-w-4xl text-sm text-text-secondary">This page exposes exactly what the current backend supports today: user profile state and health. Preference editing can be wired the moment the PATCH endpoint is implemented.</p>
      </header>
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="panel space-y-4 p-6">
          <h2 className="font-display text-3xl text-text-primary">Account snapshot</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Letterboxd</p>
              <p className="mt-2 text-sm text-text-primary">@{user.letterboxd_username}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Country</p>
              <p className="mt-2 text-sm text-text-primary">{user.country_code}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Preferred format</p>
              <p className="mt-2 text-sm text-text-primary">{user.preferred_format}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Last sync</p>
              <p className="mt-2 text-sm text-text-primary">{formatDate(user.last_synced_at)}</p>
            </div>
          </div>
        </section>
        <section className="panel space-y-4 p-6">
          <h2 className="font-display text-3xl text-text-primary">Backend health</h2>
          {health ? (
            <div className="space-y-3">
              <p className="text-sm text-text-secondary">Status: <span className="text-text-primary">{health.status}</span></p>
              <p className="text-sm text-text-secondary">API version: <span className="text-text-primary">{health.version}</span></p>
              <p className="text-sm text-text-secondary">CORS is enabled for the frontend dev origins so browser requests can succeed.</p>
            </div>
          ) : healthError ? (
            <ErrorState title="Health check failed" message={healthError} />
          ) : (
            <LoadingSpinner label="Checking backend health…" />
          )}
        </section>
      </div>
    </div>
  );
}
