import type { CreatedUser, CreateUserInput, HealthPayload, ScrapeJob, UserProfile } from "@/types/user";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type Envelope<T> = {
  success: boolean;
  data: T;
  error: {
    code: string;
    message: string;
  } | null;
};

export class APIError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "APIError";
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  const payload = (await response.json()) as Envelope<T>;

  if (!response.ok || !payload.success) {
    throw new APIError(payload.error?.code ?? "REQUEST_FAILED", payload.error?.message ?? "Request failed");
  }

  return payload.data;
}

export const healthApi = {
  get: () => request<HealthPayload>("/health")
};

export const usersApi = {
  create: (input: CreateUserInput) =>
    request<CreatedUser>("/users", {
      method: "POST",
      body: JSON.stringify(input)
    }),
  get: (userId: string) => request<UserProfile>(`/users/${userId}`)
};

export const scrapeApi = {
  startLetterboxd: (user_id: string, mode: "full" | "incremental" = "full") =>
    request<{ job_id: string; status: string; estimated_seconds: number }>("/scrape/letterboxd", {
      method: "POST",
      body: JSON.stringify({ user_id, mode })
    }),
  status: async (jobId: string): Promise<ScrapeJob> => {
    const data = await request<{
      job_id: string;
      status: ScrapeJob["status"];
      progress: ScrapeJob["progress"];
      error: ScrapeJob["error"];
    }>(`/scrape/status/${jobId}`);

    return {
      job_id: data.job_id,
      status: data.status,
      progress: data.progress,
      error: data.error
    };
  }
};
