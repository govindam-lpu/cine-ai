import Link from "next/link";

import { cn } from "@/lib/utils";

type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  className?: string;
};

export default function EmptyState({ title, description, actionLabel, actionHref, className }: EmptyStateProps) {
  return (
    <section className={cn("panel flex flex-col gap-4 p-8", className)}>
      <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Nothing here yet</p>
      <div className="space-y-2">
        <h2 className="font-display text-3xl text-text-primary">{title}</h2>
        <p className="max-w-2xl text-sm text-text-secondary">{description}</p>
      </div>
      {actionLabel && actionHref ? (
        <Link className="button-primary w-fit" href={actionHref}>
          {actionLabel}
        </Link>
      ) : null}
    </section>
  );
}
