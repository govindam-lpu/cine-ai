"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";

// Free text is the primary input; the suggestions are one-tap quick-fills (they submit immediately).
const SUGGESTIONS = ["Uplifting", "Dark", "Cerebral", "Cozy", "Tense", "A slow burn", "Something foreign"];

export default function MoodPrompt({
  value,
  onSubmit,
  disabled,
}: {
  value: string;
  onSubmit: (prompt: string) => void;
  disabled?: boolean;
}) {
  const [text, setText] = useState(value);

  function submit(next: string) {
    setText(next);
    onSubmit(next.trim());
  }

  return (
    <div className="space-y-3">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit(text);
        }}
      >
        <input
          type="text"
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          placeholder="What are you in the mood for? e.g. a slow, melancholic sci-fi"
          aria-label="What are you in the mood for?"
          className="input-base flex-1"
        />
        <button type="submit" disabled={disabled} className="button-primary px-4 text-xs disabled:opacity-50">
          Find
        </button>
      </form>
      <div className="flex flex-wrap gap-2">
        {value ? (
          <button
            onClick={() => submit("")}
            className="rounded-full border border-border-default px-3 py-1 text-xs text-text-secondary hover:text-text-primary"
          >
            Clear
          </button>
        ) : null}
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            disabled={disabled}
            onClick={() => submit(s)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors disabled:opacity-50",
              value.toLowerCase() === s.toLowerCase()
                ? "border-border-accent bg-[var(--accent-glow)] text-accent"
                : "border-border-default text-text-secondary hover:text-text-primary",
            )}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
