import Link from "next/link";

import UsernameGate from "@/components/app/UsernameGate";

export default function HomePage() {
  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-12">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(232,197,71,0.12),transparent_48%)]" />
      <div className="relative z-10 flex w-full max-w-3xl flex-col items-center gap-8 text-center">
        <div className="space-y-4">
          <h1 className="font-display text-5xl uppercase tracking-[0.15em] text-text-primary sm:text-7xl">Cinerex</h1>
          <p className="mx-auto max-w-2xl text-lg text-text-secondary sm:text-xl">Film recommendations that know you. Not what you watched. Who you are.</p>
        </div>
        <UsernameGate />
        <p className="text-xs uppercase tracking-[0.22em] text-text-muted">Trusted by taste. Not an algorithm.</p>
        <div className="grid w-full gap-4 pt-4 sm:grid-cols-3">
          {[
            ["Connect", "Create a profile with just your Letterboxd username."],
            ["Sync", "Run the backend scraper and watch progress in real time."],
            ["Explore", "Step into the recommendation and taste UI immediately."]
          ].map(([title, copy]) => (
            <div key={title} className="panel p-4 text-left">
              <h2 className="font-display text-2xl text-text-primary">{title}</h2>
              <p className="mt-2 text-sm text-text-secondary">{copy}</p>
            </div>
          ))}
        </div>
        <Link className="text-sm text-text-secondary underline-offset-4 hover:underline" href="/settings">
          Or inspect the connected app status first
        </Link>
      </div>
    </section>
  );
}
