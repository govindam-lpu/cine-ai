import { SlidersHorizontal } from "lucide-react";

import type { UserProfile } from "@/types/user";

type FilterSidebarProps = {
  user: UserProfile | null;
  mood: string;
  setMood: (value: string) => void;
};

export default function FilterSidebar({ user, mood, setMood }: FilterSidebarProps) {
  const chips = user?.streaming_services.length
    ? user.streaming_services.map((service) => service.provider_name)
    : ["Netflix", "Prime Video", "MUBI", "Max"];

  return (
    <aside className="panel space-y-6 p-5">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-[6px] border border-border-default text-cyan">
          <SlidersHorizontal size={18} />
        </span>
        <div>
          <p className="eyebrow">Lens</p>
          <h2 className="font-display text-2xl text-text-primary">Tune the slate</h2>
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Format</p>
        <div className="grid grid-cols-3 gap-2 text-xs uppercase tracking-[0.14em]">
          {(["films", "shows", "both"] as const).map((format) => (
            <div
              key={format}
              className={`rounded-[6px] border px-3 py-2 text-center ${user?.preferred_format === format ? "border-accent bg-[rgba(243,201,79,0.08)] text-text-primary" : "border-border-default text-text-secondary"}`}
            >
              {format}
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Mood</p>
        <button className="w-full rounded-[6px] border border-border-default bg-[rgba(245,241,234,0.03)] px-3 py-2 text-left text-sm text-text-secondary" onClick={() => setMood(mood ? "" : "Want to Think")} type="button">
          {mood || "No mood selected"}
        </button>
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Streaming</p>
        <div className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <span key={chip} className="rounded-[999px] border border-border-default bg-[rgba(245,241,234,0.03)] px-3 py-1 text-xs text-text-secondary">{chip}</span>
          ))}
        </div>
      </div>
    </aside>
  );
}
