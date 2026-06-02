import Link from "next/link";
import { ArrowRight } from "lucide-react";

import TasteDNACard from "@/components/taste/TasteDNACard";
import type { DerivedTasteProfile } from "@/types/taste";
import type { UserProfile } from "@/types/user";

export default function DNAReveal({ user, taste }: { user: UserProfile | null; taste: DerivedTasteProfile }) {
  return (
    <section className="space-y-6">
      <div>
        <p className="eyebrow">Step 3 / Ready</p>
        <h2 className="mt-2 font-display text-5xl text-text-primary">Your profile is connected</h2>
        <p className="mt-3 max-w-3xl text-sm text-text-secondary">Your movie history is now available to the product shell.</p>
      </div>
      <TasteDNACard taste={taste} user={user} />
      <div className="flex flex-wrap gap-3">
        <Link className="button-primary gap-2" href="/recommendations">
          Find something to watch
          <ArrowRight size={16} />
        </Link>
        <Link className="button-secondary" href="/taste">
          Open Taste DNA
        </Link>
      </div>
    </section>
  );
}
