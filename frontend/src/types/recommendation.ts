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

export type RecommendationPayload = {
  recommendations: Recommendation[];
  wild_card: Recommendation | null;
  anti_recommendations: AntiRecommendation[];
  generated_at: string;
  basis?: {
    films_analyzed: number;
    top_genres: Array<{ genre: string; count: number; avg_rating?: number | null }>;
    mood?: string | null;
  };
};
