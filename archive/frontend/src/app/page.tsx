import Link from "next/link";
import { Activity, Clapperboard, Sparkles } from "lucide-react";

import UsernameGate from "@/components/app/UsernameGate";

const posters = [
  "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
  "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
  "/tFXcEccSQMf3lfhfXKSU9iRBpa3.jpg",
  "/7LEI8ulZzO5gy9Ww2NVCrKmHeDZ.jpg",
  "/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg",
  "/8sEL4RERUw4x0jD6caKQisRz6Lk.jpg"
];

export default function HomePage() {
  return (
    <section className="relative min-h-screen overflow-hidden px-5 py-6 sm:px-8">
      <div className="absolute inset-y-0 right-0 hidden w-[54vw] grid-cols-3 gap-3 p-6 opacity-70 lg:grid">
        {posters.map((poster, index) => (
          <div key={poster} className={`overflow-hidden rounded-[8px] border border-border-subtle bg-bg-elevated ${index % 2 ? "translate-y-10" : ""}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="h-full min-h-[280px] w-full object-cover" src={`https://image.tmdb.org/t/p/w500${poster}`} />
          </div>
        ))}
        <div className="absolute inset-0 bg-[linear-gradient(90deg,var(--bg-base)_0%,rgba(13,16,20,0.7)_34%,rgba(13,16,20,0.14)_100%)]" />
      </div>

      <div className="relative z-10 flex min-h-[calc(100vh-3rem)] max-w-7xl flex-col justify-between">
        <nav className="flex items-center justify-between">
          <Link className="font-display text-2xl uppercase tracking-[0.18em] text-text-primary" href="/">
            Cinerex
          </Link>
          <Link className="button-secondary hidden px-4 py-2 text-xs sm:inline-flex" href="/settings">
            System Status
          </Link>
        </nav>

        <div className="grid gap-10 py-12 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end">
          <div className="space-y-8">
            <div className="space-y-5">
              <p className="eyebrow">Taste-based cinema intelligence</p>
              <h1 className="hero-title text-text-primary">Cinerex</h1>
              <p className="max-w-2xl text-xl leading-8 text-text-secondary">
                Film recommendations shaped by the patterns behind your ratings, rewatches, and recent obsessions.
              </p>
            </div>
            <UsernameGate />
          </div>

          <div className="panel space-y-5 p-5">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-[6px] border border-border-accent text-accent">
                <Activity size={18} />
              </span>
              <div>
                <p className="eyebrow">MVP Status</p>
                <p className="text-sm text-text-secondary">Letterboxd sync is live. AI profile and rec engines are next.</p>
              </div>
            </div>
            <div className="grid gap-3">
              {[
                [Clapperboard, "Import", "Public Letterboxd history"],
                [Sparkles, "Profile", "Taste DNA workspace"],
                [Activity, "Explore", "Recommendation dashboard"]
              ].map(([Icon, title, copy]) => (
                <div key={title as string} className="stat-card flex items-center gap-3">
                  <span className="text-cyan"><Icon size={18} /></span>
                  <div>
                    <p className="text-sm font-medium text-text-primary">{title as string}</p>
                    <p className="text-xs text-text-muted">{copy as string}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-3 border-t border-border-default py-5 text-sm text-text-muted sm:grid-cols-3">
          <p>Private by default</p>
          <p>No Letterboxd password needed</p>
          <p>Built for films first, TV later</p>
        </div>
      </div>
    </section>
  );
}
