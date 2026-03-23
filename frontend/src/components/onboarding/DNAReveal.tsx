import Link from "next/link";

import TasteDNACard from "@/components/taste/TasteDNACard";
import type { DerivedTasteProfile } from "@/types/taste";
import type { UserProfile } from "@/types/user";

export default function DNAReveal({ user, taste }: { user: UserProfile | null; taste: DerivedTasteProfile }) {
  return (
    <section className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Step 3 · First reveal</p>
        <h2 className="mt-2 font-display text-4xl text-text-primary">Your profile is connected</h2>
        <p className="mt-3 max-w-3xl text-sm text-text-secondary">The dedicated taste endpoint is still pending, but your frontend now transitions cleanly into the Taste DNA experience with real backend user + sync data.</p>
      </div>
      <TasteDNACard taste={taste} user={user} />
      <div className="flex flex-wrap gap-3">
        <Link className="button-primary" href="/recommendations">
          Now find me something to watch →
        </Link>
        <Link className="button-secondary" href="/taste">
          Open full Taste DNA page
        </Link>
      </div>
    </section>
  );
}
