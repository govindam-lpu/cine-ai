export type Film = {
  tmdb_id: number;
  media_type: "film" | "show";
  title: string;
  release_year: number;
  runtime_minutes: number;
  genres: string[];
  directors?: string[];
  poster_path?: string | null;
  tmdb_rating?: number | null;
  overview?: string | null;
};

export type StreamingOption = {
  provider_id: number;
  provider_name: string;
  type?: string;
};
