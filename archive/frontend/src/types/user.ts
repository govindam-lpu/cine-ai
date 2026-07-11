export type PreferredFormat = "films" | "shows" | "both";
export type SyncStatus = "pending" | "started" | "scraping" | "enriching" | "profiling" | "complete" | "error";

export type UserProfile = {
  user_id: string;
  letterboxd_username: string | null;
  country_code: string;
  preferred_format: PreferredFormat;
  last_synced_at: string | null;
  sync_status: SyncStatus;
  total_films_watched: number;
  has_taste_profile: boolean;
};

export type CreatedUser = {
  user_id: string;
  letterboxd_profile: {
    username: string;
    display_name: string | null;
    avatar_url: string | null;
    is_private: boolean;
  };
  sync_status: SyncStatus;
};

export type CreateUserInput = {
  letterboxd_username: string;
  country_code?: string;
  preferred_format?: PreferredFormat;
};

export type ScrapeJob = {
  job_id: string;
  status: SyncStatus;
  estimated_seconds?: number;
  progress: {
    step: string;
    films_processed: number;
    films_total: number;
  };
  error?: {
    code: string;
    message: string;
  } | null;
};

export type HealthPayload = {
  status: string;
  version: string;
};
