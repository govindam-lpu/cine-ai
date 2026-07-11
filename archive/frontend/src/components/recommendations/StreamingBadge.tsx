import type { StreamingOption } from "@/types/film";

export default function StreamingBadge({ option }: { option: StreamingOption }) {
  return <span className="inline-flex border border-border-default px-2 py-1 text-xs text-text-secondary">{option.provider_name}</span>;
}
