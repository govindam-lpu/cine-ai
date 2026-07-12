// Sample API-shaped data for component tests (not imported by app code).
import type { Evidence, Recommendation } from "@/lib/api";

export const sampleEvidence: Evidence = {
  counts: { films: 120, rated: 98, unrated: 22, rewatched: 9 },
  baseline_rating: 3.7,
  rating_std: 0.9,
  genre_affinity: [
    { genre: "Drama", n: 40, share: 0.4, mean_rating: 4.2, delta: 0.5 },
    { genre: "Science Fiction", n: 18, share: 0.18, mean_rating: 4.4, delta: 0.7 },
    { genre: "Comedy", n: 12, share: 0.12, mean_rating: 3.1, delta: -0.6 },
  ],
  era_affinity: [{ decade: "1970s", n: 20, share: 0.2, mean_rating: 4.3, delta: 0.6 }],
  crew_affinity: {
    director: [{ name: "Andrei Tarkovsky", n: 5, mean_rating: 4.6, delta: 0.9 }],
    cinematographer: [],
    composer: [],
  },
  contrarianism: { value: 0.4, n: 98, confidence: "high" },
  obscurity_preference: { value: -0.5, n: 98, confidence: "high" },
  patience: { value: 0.3, n: 90, confidence: "high" },
  rewatch_signal: { count: 9, top_genres: ["Drama"], top_directors: ["Andrei Tarkovsky"] },
  recency_drift: { recent_n: 20, recent_top_genres: ["Drama"], lifetime_top_genres: ["Drama"], rising_genres: [] },
  languages: [{ language: "en", n: 70, share: 0.58 }],
  seeds: { genres: ["Drama", "Science Fiction"], decades: ["1970s"], languages: ["en"] },
};

export const sampleRec: Recommendation = {
  tmdb_id: 424,
  title: "Schindler's List",
  year: 1993,
  poster_path: "/abc.jpg",
  overview: "A German industrialist saves lives during the Holocaust.",
  tmdb_rating: 8.6,
  tmdb_vote_count: 15234,
  score: 0.47,
  signals: [
    { factor: "similarity", strength: 0.28, detail: "It sits close to the center of what you rate highly." },
    { factor: "director", strength: 0.2, detail: "You rate Steven Spielberg's films above your average.", name: "Steven Spielberg" },
    { factor: "genre", strength: 0.15, detail: "Drama is one of your higher-rated genres.", name: "Drama" },
  ],
  reason: "It leans into the slow, historical drama you rate highest, and its director is one you already trust.",
  at_capacity: false,
};
