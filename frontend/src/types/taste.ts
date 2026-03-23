export type ToneProfile = {
  dark_light: number;
  slow_fast: number;
  emotional_intellectual: number;
  arthouse_mainstream: number;
};

export type GenreStat = {
  genre: string;
  value: number;
  note?: string;
};

export type TasteTimelineEntry = {
  label: string;
  description: string;
};

export type DerivedTasteProfile = {
  summary: string;
  fingerprint: string;
  top_genres: GenreStat[];
  preferred_eras: GenreStat[];
  tone_profile: ToneProfile;
  invisible_preferences: string[];
  crew_affinities: string[];
  negative_signals: string[];
  emotional_aftertastes: GenreStat[];
  pretension_score: number;
  timeline: TasteTimelineEntry[];
  backendReady: boolean;
};
