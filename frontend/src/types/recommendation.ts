import type { Film, StreamingOption } from "@/types/film";

export type RecommendationConfidence = "high" | "medium" | "wild";

export type Recommendation = {
  film: Film;
  reason: string;
  confidence: RecommendationConfidence;
  tags: string[];
  streaming: StreamingOption[];
  predicted_rating: number;
  is_wild_card?: boolean;
};

export type AntiRecommendation = {
  film: Film;
  reason: string;
  confidence: RecommendationConfidence;
};
