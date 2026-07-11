"use client";

import { useEffect, useState } from "react";

export function LoadingState({ messages, sub }: { messages: string[]; sub?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((v) => (v + 1) % messages.length), 2200);
    return () => clearInterval(id);
  }, [messages.length]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 text-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border-default border-t-accent" />
      <p className="font-display text-2xl text-text-primary">{messages[i]}</p>
      {sub ? <p className="font-mono text-xs text-text-muted">{sub}</p> : null}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="panel flex flex-col items-center gap-3 p-10 text-center">
      <p className="font-display text-3xl text-text-primary">{title}</p>
      {children ? <div className="max-w-md text-sm text-text-secondary">{children}</div> : null}
    </div>
  );
}

export function ErrorState({ title, message, onRetry }: { title: string; message?: string; onRetry?: () => void }) {
  return (
    <div className="panel flex flex-col items-center gap-4 p-10 text-center">
      <p className="font-display text-3xl text-negative">{title}</p>
      {message ? <p className="max-w-md text-sm text-text-secondary">{message}</p> : null}
      {onRetry ? (
        <button className="button-secondary px-4 py-2 text-xs" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}
