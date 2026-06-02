const moods = ["Comfort Watch", "Need to Cry", "Want to Think", "Date Night", "Disturb Me", "Low Focus"];

type MoodSelectorProps = {
  value: string;
  onChange: (value: string) => void;
};

export default function MoodSelector({ value, onChange }: MoodSelectorProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {moods.map((mood) => {
        const active = value === mood;
        return (
          <button
            key={mood}
            className={`rounded-[999px] border px-4 py-2 text-xs uppercase tracking-[0.14em] transition ${
              active
                ? "border-accent bg-[rgba(243,201,79,0.1)] text-text-primary"
                : "border-border-default bg-[rgba(245,241,234,0.03)] text-text-secondary hover:border-border-accent"
            }`}
            onClick={() => onChange(active ? "" : mood)}
            type="button"
          >
            {mood}
          </button>
        );
      })}
    </div>
  );
}
