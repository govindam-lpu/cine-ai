"use client";

import { useEffect, useMemo, useState } from "react";

import DNAReveal from "@/components/onboarding/DNAReveal";
import LoadingTypewriter from "@/components/onboarding/LoadingTypewriter";
import UsernameInput from "@/components/onboarding/UsernameInput";
import ErrorState from "@/components/shared/ErrorState";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { APIError, scrapeApi, usersApi } from "@/lib/api";
import { useTasteProfile } from "@/hooks/useTasteProfile";
import { useUser } from "@/hooks/useUser";
import { useUserStore } from "@/stores/userStore";
import type { CreateUserInput, ScrapeJob } from "@/types/user";

export default function OnboardingClient({ initialUsername }: { initialUsername?: string }) {
  const { user, refresh } = useUser();
  const { setUser, setUserId, activeJob, setActiveJob } = useUserStore();
  const { taste, loading: tasteLoading, error: tasteError } = useTasteProfile(user);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const step = useMemo(() => {
    if (activeJob?.status === "complete" && user) return 3;
    if (activeJob) return 2;
    return 1;
  }, [activeJob, user]);

  async function handleSubmit(payload: CreateUserInput) {
    setSubmitting(true);
    setError(null);
    try {
      const created = await usersApi.create(payload);
      setUserId(created.user_id);
      const nextUser = await usersApi.get(created.user_id);
      setUser(nextUser);
      const started = await scrapeApi.startLetterboxd(created.user_id, "full");
      setActiveJob({
        job_id: started.job_id,
        status: "started",
        estimated_seconds: started.estimated_seconds,
        progress: {
          step: "Queued",
          films_processed: 0,
          films_total: 0
        }
      });
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not create your profile.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!activeJob || activeJob.status === "complete" || activeJob.status === "error") {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const job: ScrapeJob = await scrapeApi.status(activeJob.job_id);
        setActiveJob(job);
        await refresh();
      } catch (err) {
        setError(err instanceof APIError ? err.message : "Could not poll sync status.");
      }
    }, 2500);

    return () => window.clearInterval(interval);
  }, [activeJob, refresh, setActiveJob]);

  return (
    <div className="page-shell space-y-8">
      <header className="space-y-3">
        <p className="eyebrow">Onboarding</p>
        <h1 className="font-display text-5xl text-text-primary md:text-6xl">Build your profile</h1>
        <p className="max-w-3xl text-base text-text-secondary">Connect a public Letterboxd profile, import recent viewing history, and step into the recommendation workspace.</p>
      </header>

      {error ? <ErrorState message={error} /> : null}

      {step === 1 ? <UsernameInput initialUsername={initialUsername} loading={submitting} onSubmit={handleSubmit} /> : null}
      {step === 2 ? (
        <div className="space-y-4">
          {submitting ? <LoadingSpinner label="Submitting your profile..." /> : null}
          <LoadingTypewriter job={activeJob} />
        </div>
      ) : null}
      {step === 3 && tasteLoading ? <LoadingSpinner label="Loading taste profile..." /> : null}
      {step === 3 && tasteError ? <ErrorState message={tasteError} title="Taste profile unavailable" /> : null}
      {step === 3 && taste ? <DNAReveal taste={taste} user={user} /> : null}
    </div>
  );
}
