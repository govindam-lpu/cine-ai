"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  getProfile,
  streamRecommendations,
  type ProfileResponse,
  type Recommendation,
} from "@/lib/api";
import MoodSelector from "@/components/MoodSelector";
import RecommendationCard from "@/components/RecommendationCard";
import TasteDNACard from "@/components/TasteDNACard";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";

const BUILDING_MESSAGES = [
  "Reading your ratings…",
  "Matching films on TMDB…",
  "Finding the patterns…",
  "Writing your taste…",
];

export default function ProfileClient({ handle }: { handle: string }) {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);

  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [recDone, setRecDone] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);
  const [mood, setMood] = useState("");
  const [rerollKey, setRerollKey] = useState(0);
  const [copied, setCopied] = useState(false);

  // Load the profile; poll while it's building. Retry (softly) on network error → "waking up".
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const p = await getProfile(handle);
        if (cancelled) return;
        setProfile(p);
        setLoadError(null);
        setWaking(false);
        if (p.status === "building") timer = setTimeout(load, 1600);
      } catch (e) {
        if (cancelled) return;
        setWaking(true);
        setLoadError(e instanceof ApiError ? e.message : "Network error");
        timer = setTimeout(load, 3000);
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [handle]);

  // Stream recommendations once ready; re-stream on mood change or re-roll. The `active` flag makes
  // it StrictMode-safe: an aborted stream's late callbacks are ignored, so a re-invoked effect
  // can't interleave or drop cards.
  useEffect(() => {
    if (profile?.status !== "ready") return;
    let active = true;
    setRecs([]);
    setRecDone(false);
    setRecError(null);
    const abort = streamRecommendations(handle, {
      mood: mood || undefined,
      onCard: (r) =>
        active &&
        setRecs((prev) => (prev.some((x) => x.tmdb_id === r.tmdb_id) ? prev : [...prev, r])),
      onDone: () => active && setRecDone(true),
      onError: (e) => active && setRecError(e.message),
    });
    return () => {
      active = false;
      abort();
    };
  }, [profile?.status, handle, mood, rerollKey]);

  const share = useCallback(() => {
    // Copying is best-effort (blocked in some contexts); the shareable URL is already the address bar.
    navigator.clipboard?.writeText(window.location.href).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }, []);

  if (waking && !profile) {
    return (
      <Shell>
        <LoadingState messages={["Waking the server up…"]} sub="First visit after a quiet spell can take ~30s." />
      </Shell>
    );
  }
  if (!profile) {
    return (
      <Shell>
        <LoadingState messages={BUILDING_MESSAGES} />
      </Shell>
    );
  }
  if (profile.status === "not_found") {
    return (
      <Shell>
        <EmptyState title="No profile here yet">
          <p>
            Nothing has been uploaded for <span className="text-text-primary">{handle}</span>.{" "}
            <Link className="text-accent" href="/">
              Upload an export
            </Link>
            .
          </p>
        </EmptyState>
      </Shell>
    );
  }
  if (profile.status === "building") {
    const job = profile.job;
    const sub =
      job.queue_position > 0
        ? `You're #${job.queue_position} in line`
        : job.films_total
        ? `${job.films_processed}/${job.films_total} films`
        : undefined;
    return (
      <Shell>
        <LoadingState messages={BUILDING_MESSAGES} sub={sub} />
      </Shell>
    );
  }
  if (profile.status === "needs_more_films") {
    return (
      <Shell>
        <EmptyState title="A little more to go">
          <p>{profile.message}</p>
          <Link className="mt-3 inline-block text-accent" href="/">
            Upload again
          </Link>
        </EmptyState>
      </Shell>
    );
  }
  if (profile.status === "failed") {
    return (
      <Shell>
        <ErrorState title="That didn't work" message={profile.message} onRetry={() => location.reload()} />
      </Shell>
    );
  }

  // ready
  return (
    <Shell>
      <div className="flex items-center justify-between gap-4">
        <Link className="font-display text-xl uppercase tracking-[0.14em] text-text-primary" href="/">
          Cinerex
        </Link>
        <button className="button-secondary px-3 py-1.5 text-xs" onClick={share}>
          {copied ? "Link copied" : "Share"}
        </button>
      </div>

      <TasteDNACard
        summary={profile.summary}
        evidence={profile.evidence}
        displayName={profile.display_name}
        handle={profile.handle}
      />

      <section className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-2xl text-text-primary">Eight for you</h2>
          <button
            className="button-secondary px-3 py-1.5 text-xs"
            onClick={() => setRerollKey((k) => k + 1)}
          >
            Re-roll
          </button>
        </div>
        <MoodSelector value={mood} onChange={setMood} />

        {recError && recs.length === 0 ? (
          <ErrorState title="Couldn't load recommendations" message={recError} onRetry={() => setRerollKey((k) => k + 1)} />
        ) : recs.length === 0 && !recDone ? (
          <LoadingState messages={["Finding your films…"]} />
        ) : (
          <div className="grid gap-4">
            {recs.map((rec, i) => (
              <RecommendationCard key={rec.tmdb_id} rec={rec} index={i + 1} />
            ))}
            {!recDone ? <p className="font-mono text-xs text-text-muted">writing more…</p> : null}
          </div>
        )}
      </section>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-4xl space-y-8 px-5 py-8">{children}</main>;
}
