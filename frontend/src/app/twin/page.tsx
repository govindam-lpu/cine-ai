"use client";

import EmptyState from "@/components/shared/EmptyState";

export default function TwinPage() {
  return (
    <div className="page-shell space-y-6">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-text-muted">Film twin</p>
        <h1 className="font-display text-5xl text-text-primary">Find your nearest taste neighbor</h1>
        <p className="max-w-3xl text-sm text-text-secondary">The backend contract includes a twin finder, but the current codebase hasn’t implemented that route yet.</p>
      </header>
      <EmptyState description="This page is ready to accept the eventual /twin payload without changing the product shell or navigation." title="Twin matching coming soon" />
    </div>
  );
}
