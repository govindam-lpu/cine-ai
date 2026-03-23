"use client";

import EmptyState from "@/components/shared/EmptyState";
import { useCompatibility } from "@/hooks/useCompatibility";

export default function CompatibilityPage() {
  const compatibility = useCompatibility();

  return (
    <div className="page-shell space-y-6">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-text-muted">Compatibility mode</p>
        <h1 className="font-display text-5xl text-text-primary">Shared taste, mapped beautifully</h1>
        <p className="max-w-3xl text-sm text-text-secondary">The layout is ready, but the backend compatibility route is still a stub. Once it exists, this page can render overlap scores, divergence points, and bridge picks without a redesign.</p>
      </header>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.2em] text-text-muted">User A</p>
          <h2 className="mt-3 font-display text-3xl text-text-primary">Mini DNA card</h2>
          <p className="mt-3 text-sm text-text-secondary">This side is reserved for the initiating profile.</p>
        </div>
        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.2em] text-text-muted">User B</p>
          <h2 className="mt-3 font-display text-3xl text-text-primary">Comparison card</h2>
          <p className="mt-3 text-sm text-text-secondary">This side will render the comparison profile and bridge picks.</p>
        </div>
      </div>
      <EmptyState description={compatibility.message} title="Compatibility endpoint pending" />
    </div>
  );
}
