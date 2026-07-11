import type { RecommendationConfidence } from "@/types/recommendation";
import { cn } from "@/lib/utils";

const styles: Record<RecommendationConfidence, string> = {
  high: "border-positive/30 bg-[rgba(126,200,122,0.12)] text-positive",
  medium: "border-warning/30 bg-[rgba(232,160,71,0.12)] text-warning",
  wild: "border-accent border-dashed bg-[rgba(232,197,71,0.1)] text-accent"
};

export default function ConfidenceBadge({ confidence }: { confidence: RecommendationConfidence }) {
  const label = confidence === "high" ? "High match" : confidence === "wild" ? "Wild card" : "Likely";

  return <span className={cn("inline-flex items-center border px-2 py-1 text-[11px] uppercase tracking-[0.16em]", styles[confidence])}>{label}</span>;
}
