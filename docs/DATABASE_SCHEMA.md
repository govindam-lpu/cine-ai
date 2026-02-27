# Cinerex — Database Schema

Database: Supabase (Postgres 15 + pgvector extension)
All tables use UUID primary keys. All timestamps are `timestamptz` in UTC.

Enable the vector extension before running migrations:
```sql
create extension if not exists vector;
```

---

## Tables Overview

| Table | Purpose |
|---|---|
| `users` | Core user accounts |
| `letterboxd_profiles` | Linked Letterboxd profiles per user |
| `serializd_profiles` | Linked Serializd profiles per user |
| `films` | TMDB-enriched film/show metadata cache |
| `watch_history` | Every film/show a user has watched |
| `taste_profiles` | AI-generated taste profile per user |
| `streaming_services` | Which services a user subscribes to |
| `watchlist` | User's saved-to-watch films |
| `predictions` | Pre-watch rating predictions + outcomes |
| `compatibility_sessions` | Multi-profile compatibility analysis results |
| `film_twins` | Matched film twin pairs |
| `post_watch_reflections` | User's post-watch answers |
| `taste_challenges` | Weekly challenge tracking |

---

## Table Definitions

### `users`
Core Cinerex account. Created when a user first enters their Letterboxd username.

```sql
create table users (
  id                uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  -- Identity
  email             text unique,                        -- optional, for future auth
  display_name      text,                               -- optional

  -- Preferences
  country_code      text default 'US',                  -- ISO 3166-1 alpha-2, for streaming availability
  preferred_format  text default 'both'                 -- 'films' | 'shows' | 'both'
    check (preferred_format in ('films', 'shows', 'both')),

  -- Sync state
  last_synced_at    timestamptz,
  sync_status       text default 'pending'
    check (sync_status in ('pending', 'scraping', 'enriching', 'profiling', 'complete', 'error')),
  sync_error        text                                -- error message if sync failed
);
```

---

### `letterboxd_profiles`
Stores the user's linked Letterboxd profile and scrape state.

```sql
create table letterboxd_profiles (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references users(id) on delete cascade,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  username          text not null,                      -- Letterboxd username
  profile_url       text not null,                      -- https://letterboxd.com/{username}/
  display_name      text,                               -- as shown on Letterboxd
  avatar_url        text,
  bio               text,

  -- Scrape state
  last_scraped_at   timestamptz,
  total_films       integer default 0,
  is_private        boolean default false,              -- if profile turned private after scrape

  unique (user_id, username)
);
```

---

### `serializd_profiles`
Same pattern as Letterboxd but for TV shows.

```sql
create table serializd_profiles (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references users(id) on delete cascade,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  username          text not null,
  profile_url       text not null,
  display_name      text,

  last_scraped_at   timestamptz,
  total_shows       integer default 0,
  is_private        boolean default false,

  unique (user_id, username)
);
```

---

### `films`
Shared TMDB metadata cache. One row per unique TMDB item. Not user-specific.
"Films" here means both films and TV shows (distinguished by `media_type`).

```sql
create table films (
  id                uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  -- TMDB identity
  tmdb_id           integer not null,
  media_type        text not null check (media_type in ('film', 'show')),
  imdb_id           text,

  -- Core metadata
  title             text not null,
  original_title    text,
  release_year      integer,
  runtime_minutes   integer,                            -- null for shows (variable)
  overview          text,
  tagline           text,
  original_language text,
  origin_countries  text[],

  -- Classification
  genres            text[],
  keywords          text[],
  themes            text[],                             -- AI-extracted thematic tags

  -- Crew (denormalized for query performance)
  directors         text[],
  cinematographers  text[],
  composers         text[],
  writers           text[],
  lead_cast         text[],                             -- top 5 billed

  -- Ratings
  tmdb_rating       numeric(3,1),
  tmdb_vote_count   integer,
  imdb_rating       numeric(3,1),
  metacritic_score  integer,
  rt_score          integer,

  -- Visuals
  poster_path       text,                              -- TMDB path, prepend base URL
  backdrop_path     text,

  -- Production
  production_companies text[],
  collection_name   text,                              -- if part of a series/franchise

  -- Embedding for semantic matching
  embedding         vector(1536),                      -- OpenAI text-embedding-3-small

  unique (tmdb_id, media_type)
);

-- Indexes
create index idx_films_tmdb_id on films(tmdb_id);
create index idx_films_media_type on films(media_type);
create index idx_films_release_year on films(release_year);
create index idx_films_tmdb_rating on films(tmdb_rating);
create index idx_films_embedding on films using ivfflat (embedding vector_cosine_ops);
```

---

### `watch_history`
Every film or show a user has watched, from Letterboxd or Serializd.

```sql
create table watch_history (
  id                uuid primary key default gen_random_uuid(),
  created_at        timestamptz not null default now(),

  user_id           uuid not null references users(id) on delete cascade,
  film_id           uuid not null references films(id),

  -- Source
  source            text not null check (source in ('letterboxd', 'serializd', 'manual')),

  -- Watch data
  user_rating       numeric(3,1),                      -- 0.5 to 5.0, null if logged without rating
  watched_at        date,                               -- date watched (not datetime)
  is_rewatch        boolean default false,
  watch_count       integer default 1,

  -- Review
  review_text       text,                               -- user's written review if any
  review_liked      boolean,                            -- Letterboxd 'liked' heart

  -- Source IDs
  letterboxd_id     text,                               -- Letterboxd's internal entry ID

  unique (user_id, film_id, source)
);

-- Indexes
create index idx_watch_history_user_id on watch_history(user_id);
create index idx_watch_history_film_id on watch_history(film_id);
create index idx_watch_history_watched_at on watch_history(watched_at);
create index idx_watch_history_user_rating on watch_history(user_rating);
```

---

### `taste_profiles`
AI-generated taste profile. One row per user. Updated incrementally.

```sql
create table taste_profiles (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null unique references users(id) on delete cascade,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  -- AI-generated summary
  taste_summary       text not null,                    -- prose description of the viewer
  taste_fingerprint   text,                             -- one-line identity tag

  -- Genre preferences (array of {genre, avg_rating, count})
  top_genres          jsonb default '[]',

  -- Era preferences (array of {decade, avg_rating})
  preferred_eras      jsonb default '[]',

  -- Tone profile (-1.0 to 1.0 on each axis)
  tone_dark_light     numeric(4,3),                     -- -1 = very dark, 1 = very light
  tone_slow_fast      numeric(4,3),                     -- -1 = slow burn, 1 = fast paced
  tone_emotional_intellectual numeric(4,3),
  tone_arthouse_mainstream    numeric(4,3),

  -- Narrative + pacing
  narrative_preference text check (narrative_preference in ('plot','character','atmosphere','ideas')),
  pacing_preference   text check (pacing_preference in ('slow_burn','moderate','fast_paced')),
  ending_preference   text check (ending_preference in ('resolution','ambiguity','no_preference')),

  -- Crew affinities
  top_directors       text[] default '{}',
  top_cinematographers text[] default '{}',
  top_composers       text[] default '{}',

  -- Invisible preferences (AI-detected non-obvious patterns)
  invisible_preferences jsonb default '[]',             -- array of strings

  -- Negative signals
  negative_signals    jsonb default '[]',               -- array of strings

  -- Emotional aftertastes (array of {emotion, correlation_score})
  emotional_aftertastes jsonb default '[]',

  -- Behavioral scores
  pretension_score    numeric(4,3),                     -- -1 = crowd pleaser, 1 = contrarian
  runtime_correlation numeric(4,3),                     -- does longer = higher rating for them
  popularity_correlation numeric(4,3),                  -- do they prefer obscure?
  critical_alignment  numeric(4,3),                     -- do they agree with critics?

  -- Blind spots (AI-detected)
  blind_spot_decades  text[] default '{}',
  blind_spot_countries text[] default '{}',
  blind_spot_genres   text[] default '{}',

  -- Profile embedding (for Film Twin matching)
  profile_embedding   vector(1536),

  -- Metadata
  films_analyzed      integer default 0,
  profile_version     integer default 1                 -- increment on major updates
);

create index idx_taste_profiles_user_id on taste_profiles(user_id);
create index idx_taste_profiles_embedding on taste_profiles using ivfflat (profile_embedding vector_cosine_ops);
```

---

### `streaming_services`
Which streaming services a user subscribes to.

```sql
create table streaming_services (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  created_at  timestamptz not null default now(),

  -- TMDB provider IDs (https://www.themoviedb.org/talk/5f9d4b63fb5e1d0035aba6db)
  provider_id   integer not null,                       -- TMDB watch provider ID
  provider_name text not null,                          -- e.g. 'Netflix', 'MUBI'
  is_active     boolean default true,

  unique (user_id, provider_id)
);
```

---

### `watchlist`
Films the user wants to watch (imported from Letterboxd watchlist or manually added).

```sql
create table watchlist (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references users(id) on delete cascade,
  film_id       uuid not null references films(id),
  created_at    timestamptz not null default now(),

  source        text default 'letterboxd' check (source in ('letterboxd','manual')),
  rank          integer,                                -- AI-assigned priority rank
  rank_reason   text,                                   -- why this rank
  notes         text,                                   -- user's own notes

  unique (user_id, film_id)
);

create index idx_watchlist_user_id on watchlist(user_id);
create index idx_watchlist_rank on watchlist(user_id, rank);
```

---

### `predictions`
AI pre-watch rating predictions. Tracks accuracy over time.

```sql
create table predictions (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references users(id) on delete cascade,
  film_id           uuid not null references films(id),
  created_at        timestamptz not null default now(),

  predicted_rating  numeric(3,1) not null,              -- AI's predicted rating
  confidence        text check (confidence in ('high','medium','low')),
  prediction_reason text,

  -- Filled in after user watches and reports back
  actual_rating     numeric(3,1),
  reported_at       timestamptz,
  delta             numeric(3,1),                       -- abs(predicted - actual)

  unique (user_id, film_id)
);

create index idx_predictions_user_id on predictions(user_id);
```

---

### `compatibility_sessions`
Results of a multi-profile compatibility analysis.

```sql
create table compatibility_sessions (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),

  -- Initiated by this user
  initiated_by    uuid not null references users(id) on delete cascade,

  -- All profiles involved (array of Letterboxd usernames — may include non-users)
  profiles        text[] not null,

  -- Analysis results
  overlap_score   numeric(5,2),                         -- 0–100
  shared_traits   jsonb default '[]',
  divergence_points jsonb default '[]',

  -- Recommendations
  recommended_films jsonb default '[]',                 -- array of {tmdb_id, reason}
  bridge_pick       jsonb,                              -- single {tmdb_id, reason}
  compromise_pick   jsonb                               -- single {tmdb_id, reason}
);

create index idx_compatibility_sessions_initiated_by on compatibility_sessions(initiated_by);
```

---

### `film_twins`
Matched film twin pairs (opt-in, based on profile embedding similarity).

```sql
create table film_twins (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),

  user_id_a       uuid not null references users(id) on delete cascade,
  user_id_b       uuid not null references users(id) on delete cascade,

  similarity_score numeric(5,4) not null,               -- cosine similarity 0–1
  shared_traits    jsonb default '[]',

  -- Opt-in status for both parties
  opted_in_a       boolean default false,
  opted_in_b       boolean default false,

  check (user_id_a < user_id_b)                        -- prevents duplicate pairs
);

create index idx_film_twins_user_a on film_twins(user_id_a);
create index idx_film_twins_user_b on film_twins(user_id_b);
```

---

### `post_watch_reflections`
Optional post-watch questions answered by the user.

```sql
create table post_watch_reflections (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(id) on delete cascade,
  film_id         uuid not null references films(id),
  created_at      timestamptz not null default now(),

  stayed_with_you text,                                 -- "What stayed with you?"
  would_change    text,                                 -- "What would you have changed?"

  -- Used in next taste profile update
  processed       boolean default false,

  unique (user_id, film_id)
);
```

---

### `taste_challenges`
Weekly taste challenge tracking.

```sql
create table taste_challenges (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(id) on delete cascade,
  created_at      timestamptz not null default now(),

  challenge_type  text not null,                        -- 'new_country' | 'old_decade' | 'long_runtime' | etc.
  challenge_text  text not null,                        -- human-readable challenge description
  suggested_film_id uuid references films(id),

  week_of         date not null,                        -- ISO week start date (Monday)
  completed       boolean default false,
  completed_at    timestamptz,
  completed_with_film_id uuid references films(id),     -- what they actually watched

  unique (user_id, week_of)
);
```

---

## Row Level Security (RLS)

Enable RLS on all user-data tables. Users can only read and write their own rows.

```sql
-- Example for watch_history (repeat pattern for all user tables)
alter table watch_history enable row level security;

create policy "Users can view own watch history"
  on watch_history for select
  using (auth.uid() = user_id);

create policy "Users can insert own watch history"
  on watch_history for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own watch history"
  on watch_history for delete
  using (auth.uid() = user_id);
```

Apply the same pattern to: `users`, `letterboxd_profiles`, `serializd_profiles`, `taste_profiles`, `streaming_services`, `watchlist`, `predictions`, `compatibility_sessions`, `film_twins`, `post_watch_reflections`, `taste_challenges`.

The `films` table is public read, backend-write only (no RLS select restriction, but insert/update restricted to service role).

---

## Updated_at Trigger

Apply to all tables with an `updated_at` column:

```sql
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Apply to each relevant table
create trigger set_updated_at
  before update on users
  for each row execute procedure update_updated_at();
```
