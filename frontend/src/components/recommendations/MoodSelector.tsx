const moods = ["Comfort Watch", "Need to Cry", "Want to Think", "Date Night", "Disturb Me", "Can’t Focus"];

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
            className={`border px-3 py-2 text-xs uppercase tracking-[0.14em] transition ${
              active
                ? "border-accent bg-[rgba(232,197,71,0.08)] text-text-primary"
                : "border-border-default bg-bg-surface text-text-secondary hover:scale-[1.02]"
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
