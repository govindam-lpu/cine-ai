import { cn } from "@/lib/cn";

// Phase 0 placeholder. The real "door" screen — upload control + optional handle — is Phase 6.
// Kept deliberately plain and dependency-light so it renders in tests and proves the harness.
export default function Home() {
  return (
    <main className={cn("mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6")}>
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Cinerex</p>
      <h1 className="mt-4 font-display text-5xl leading-none">
        A taste-based film recommender.
      </h1>
      <p className="mt-6 max-w-prose text-text-secondary">
        Upload your Letterboxd export and get a taste profile plus eight recommendations, each
        with a real reason. No account, no scraping.
      </p>
      <p className="mt-8 font-mono text-xs text-text-muted">Scaffold running — Phase 0.</p>
    </main>
  );
}
