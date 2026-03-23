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
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Filter</p>
        <h2 className="mt-2 font-display text-2xl text-text-primary">Recommendation lens</h2>
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Format</p>
        <div className="grid grid-cols-3 gap-2 text-xs uppercase tracking-[0.14em]">
          {(["films", "shows", "both"] as const).map((format) => (
            <div
              key={format}
              className={`border px-3 py-2 text-center ${user?.preferred_format === format ? "border-accent text-text-primary" : "border-border-default text-text-secondary"}`}
            >
              {format}
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Mood</p>
        <button className="w-full border border-border-default px-3 py-2 text-left text-sm text-text-secondary" onClick={() => setMood(mood ? "" : "Want to Think")} type="button">
          {mood || "Choose a visible mood chip above"}
        </button>
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-text-muted">Streaming</p>
        <div className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <span key={chip} className="border border-border-default px-2 py-1 text-xs text-text-secondary">{chip}</span>
          ))}
        </div>
      </div>

      <div className="space-y-2 border-t border-border-default pt-4 text-sm text-text-secondary">
        <p>Because the backend recommendation endpoint is not shipped yet, these controls currently shape the UI state rather than live server results.</p>
      </div>
    </aside>
  );
}
