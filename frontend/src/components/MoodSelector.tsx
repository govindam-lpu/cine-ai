"use client";

import { cn } from "@/lib/cn";

export const MOODS = [
  { key: "", label: "Any mood" },
  { key: "uplifting", label: "Uplifting" },
  { key: "dark", label: "Dark" },
  { key: "cerebral", label: "Cerebral" },
  { key: "cozy", label: "Cozy" },
  { key: "tense", label: "Tense" },
];

export default function MoodSelector({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (mood: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Mood filter">
      {MOODS.map((m) => (
        <button
          key={m.key || "any"}
          disabled={disabled}
          onClick={() => onChange(m.key)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm transition-colors disabled:opacity-50",
            value === m.key
              ? "border-border-accent bg-[var(--accent-glow)] text-accent"
              : "border-border-default text-text-secondary hover:text-text-primary",
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
