// Typed client for the Cinerex backend. One place that knows the endpoint shapes.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

// --- response shapes (mirror app/schemas + evidence_json) ---

export interface JobStatus {
  job_id: string;
  handle: string;
  source: string;
  status: "queued" | "parsing" | "enriching" | "analyzing" | "complete" | "failed";
  step: string | null;
  queue_position: number;
  films_total: number;
  films_processed: number;
  films_matched: number;
  films_unmatched: number;
  error_code: string | null;
  error_message: string | null;
}

export interface Signal {
  value: number | null;
  n: number;
  confidence: string;
}

export interface GenreAffinity {
  genre: string;
  n: number;
  share: number;
  mean_rating: number | null;
  delta: number | null;
}

export interface EraAffinity {
  decade: string;
  n: number;
  share: number;
  mean_rating: number | null;
  delta: number | null;
}

export interface CrewMember {
  name: string;
  n: number;
  mean_rating: number;
  delta: number;
}

export interface Evidence {
  counts: { films: number; rated: number; unrated: number; rewatched: number };
  baseline_rating: number | null;
  rating_std: number;
  genre_affinity: GenreAffinity[];
  era_affinity: EraAffinity[];
  crew_affinity: { director: CrewMember[]; cinematographer: CrewMember[]; composer: CrewMember[] };
  contrarianism: Signal;
  obscurity_preference: Signal;
  patience: Signal;
  rewatch_signal: { count: number; top_genres: string[]; top_directors: string[] };
  recency_drift: {
    recent_n: number;
    recent_top_genres: string[];
    lifetime_top_genres: string[];
    rising_genres: string[];
  };
  languages: { language: string; n: number; share: number }[];
  seeds: { genres: string[]; decades: string[]; languages: string[] };
}

export type ProfileResponse =
  | { status: "ready"; handle: string; display_name: string | null; summary: string | null; evidence: Evidence; counts: Evidence["counts"] }
  | { status: "building"; handle: string; job: JobStatus }
  | { status: "needs_more_films"; handle: string; message: string }
  | { status: "failed"; handle: string; message: string }
  | { status: "not_found"; message: string };

export interface RecSignal {
  factor: string;
  strength: number;
  detail?: string;
  name?: string;
}

export interface Recommendation {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_path: string | null;
  overview: string | null;
  tmdb_rating: number | null;
  tmdb_vote_count: number | null;
  score: number;
  signals: RecSignal[];
  reason: string;
  at_capacity: boolean;
}

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function readError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const detail = body?.detail ?? body;
    return new ApiError(detail?.code ?? "ERROR", detail?.message ?? res.statusText);
  } catch {
    return new ApiError("ERROR", res.statusText || "Request failed");
  }
}

export async function uploadExport(file: File, handle?: string): Promise<{ handle: string; job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  if (handle) form.append("handle", handle);
  const res = await fetch(`${API_BASE}/api/profiles/upload`, { method: "POST", body: form });
  if (!res.ok) throw await readError(res);
  return res.json();
}

export async function getJob(handle: string, jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/profiles/${encodeURIComponent(handle)}/sync/${jobId}`);
  if (!res.ok) throw await readError(res);
  return res.json();
}

export async function getProfile(handle: string): Promise<ProfileResponse> {
  const res = await fetch(`${API_BASE}/api/profiles/${encodeURIComponent(handle)}`);
  const body = await res.json();
  if (res.status === 404) return { status: "not_found", message: body?.message ?? "Not found" };
  if (!res.ok) throw new ApiError(body?.code ?? "ERROR", body?.message ?? "Request failed");
  return body as ProfileResponse;
}

/** Stream recommendation cards over SSE. Returns an abort function. */
export function streamRecommendations(
  handle: string,
  opts: {
    mood?: string;
    prompt?: string;
    limit?: number;
    onCard: (rec: Recommendation) => void;
    onDone: (count: number) => void;
    onError: (err: ApiError) => void;
  },
): () => void {
  const controller = new AbortController();
  const params = new URLSearchParams();
  if (opts.mood) params.set("mood", opts.mood);
  if (opts.prompt) params.set("q", opts.prompt);
  if (opts.limit) params.set("limit", String(opts.limit));
  const url = `${API_BASE}/api/profiles/${encodeURIComponent(handle)}/recommendations?${params}`;

  (async () => {
    try {
      const res = await fetch(url, { signal: controller.signal, headers: { Accept: "text/event-stream" } });
      if (!res.ok || !res.body) {
        opts.onError(await readError(res));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const dataLine = chunk.split("\n").find((l) => l.startsWith("data: "));
          if (!dataLine) continue;
          const payload = JSON.parse(dataLine.slice(6));
          if ("count" in payload) opts.onDone(payload.count);
          else opts.onCard(payload as Recommendation);
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        opts.onError(new ApiError("STREAM_ERROR", (err as Error).message));
      }
    }
  })();

  return () => controller.abort();
}

export function posterUrl(path: string | null, size = "w342"): string | null {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

/** Letterboxd's stable per-film redirect from a TMDB id — resolves in the user's own browser
 *  (residential IP), so the Cloudflare block that stops server-side scraping never applies. */
export function letterboxdUrl(tmdbId: number): string {
  return `https://letterboxd.com/tmdb/${tmdbId}/`;
}
