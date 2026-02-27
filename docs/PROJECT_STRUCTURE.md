# Cinerex — Project Structure & File Architecture

Every file and folder in the Cinerex codebase has a defined home. Follow this structure exactly. Do not improvise new top-level directories.

---

## Root Layout

```
cinerex/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml          ← local dev: runs backend + redis
│
├── frontend/                   ← Next.js 14 app
├── backend/                    ← FastAPI app
└── docs/                       ← all spec documents (this folder)
    ├── MASTER_PROMPT.md
    ├── DESIGN.md
    ├── PROJECT_STRUCTURE.md
    ├── DATABASE_SCHEMA.md
    ├── API_CONTRACT.md
    ├── SCRAPER_SPEC.md
    ├── PRODUCT_DECISIONS.md
    └── PRIVACY_LEGAL.md
```

---

## Frontend Structure (`/frontend`)

```
frontend/
├── package.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── .env.local                  ← NEXT_PUBLIC_API_URL, Supabase keys
│
├── public/
│   ├── textures/
│   │   └── grain.png           ← film grain overlay texture
│   ├── icons/
│   └── fonts/                  ← self-hosted fallbacks if needed
│
├── src/
│   ├── app/                    ← Next.js App Router
│   │   ├── layout.tsx          ← root layout: fonts, grain overlay, metadata
│   │   ├── page.tsx            ← landing page
│   │   ├── globals.css         ← CSS variables, base styles, grain overlay
│   │   │
│   │   ├── onboarding/
│   │   │   └── page.tsx        ← 3-step onboarding flow
│   │   │
│   │   ├── recommendations/
│   │   │   └── page.tsx        ← main dashboard
│   │   │
│   │   ├── taste/
│   │   │   └── page.tsx        ← full Taste DNA page
│   │   │
│   │   ├── compatibility/
│   │   │   └── page.tsx        ← compatibility + dinner party picker
│   │   │
│   │   ├── watchlist/
│   │   │   └── page.tsx        ← watchlist ranker
│   │   │
│   │   ├── twin/
│   │   │   └── page.tsx        ← film twin finder
│   │   │
│   │   └── settings/
│   │       └── page.tsx        ← streaming services, profile prefs
│   │
│   ├── components/
│   │   ├── ui/                 ← shadcn base components (auto-generated)
│   │   │
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── BottomNav.tsx   ← mobile only
│   │   │   └── PageWrapper.tsx
│   │   │
│   │   ├── cards/
│   │   │   ├── FilmCardCompact.tsx
│   │   │   ├── FilmCardFeature.tsx
│   │   │   └── AntiRecCard.tsx
│   │   │
│   │   ├── taste/
│   │   │   ├── TasteDNACard.tsx       ← the shareable card
│   │   │   ├── ToneRadarChart.tsx
│   │   │   ├── GenreBreakdown.tsx
│   │   │   ├── CrewAffinities.tsx
│   │   │   ├── PretensionScore.tsx
│   │   │   └── TasteTimeline.tsx
│   │   │
│   │   ├── recommendations/
│   │   │   ├── RecommendationGrid.tsx
│   │   │   ├── MoodSelector.tsx
│   │   │   ├── FilterSidebar.tsx
│   │   │   ├── ConfidenceBadge.tsx
│   │   │   ├── StreamingBadge.tsx
│   │   │   └── WildCardCard.tsx
│   │   │
│   │   ├── onboarding/
│   │   │   ├── UsernameInput.tsx
│   │   │   ├── LoadingTypewriter.tsx
│   │   │   └── DNAReveal.tsx
│   │   │
│   │   └── shared/
│   │       ├── LoadingSpinner.tsx
│   │       ├── EmptyState.tsx
│   │       └── ErrorState.tsx
│   │
│   ├── hooks/
│   │   ├── useUser.ts
│   │   ├── useRecommendations.ts
│   │   ├── useTasteProfile.ts
│   │   ├── useCompatibility.ts
│   │   └── useWatchlist.ts
│   │
│   ├── lib/
│   │   ├── supabase.ts         ← supabase client init
│   │   ├── api.ts              ← typed fetch wrapper for backend API
│   │   ├── tmdb.ts             ← TMDB helper functions
│   │   └── utils.ts            ← cn(), formatRuntime(), etc.
│   │
│   ├── stores/
│   │   └── userStore.ts        ← Zustand store for user + session state
│   │
│   └── types/
│       ├── film.ts
│       ├── user.ts
│       ├── taste.ts
│       └── recommendation.ts
```

---

## Backend Structure (`/backend`)

```
backend/
├── main.py                     ← FastAPI app entry point
├── requirements.txt
├── .env                        ← all secrets (never commit)
├── Dockerfile
│
├── app/
│   ├── __init__.py
│   │
│   ├── api/                    ← route handlers
│   │   ├── __init__.py
│   │   ├── users.py            ← POST /users, GET /users/:id
│   │   ├── scrape.py           ← POST /scrape/letterboxd, /scrape/serializd
│   │   ├── profile.py          ← GET/POST /profile/:user_id
│   │   ├── recommendations.py  ← GET /recommendations/:user_id
│   │   ├── compatibility.py    ← POST /compatibility
│   │   ├── watchlist.py        ← GET/POST /watchlist/:user_id
│   │   ├── predictions.py      ← POST /predictions, PATCH /predictions/:id
│   │   └── health.py           ← GET /health
│   │
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── letterboxd.py       ← Playwright scraper for Letterboxd
│   │   ├── serializd.py        ← Playwright scraper for Serializd
│   │   └── base.py             ← shared scraper utilities
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tmdb.py             ← TMDB API wrapper
│   │   ├── omdb.py             ← OMDB API wrapper
│   │   ├── taste_profiler.py   ← AI taste profile generation
│   │   ├── recommender.py      ← recommendation engine logic
│   │   ├── embeddings.py       ← OpenAI embedding generation + storage
│   │   ├── compatibility.py    ← multi-profile compatibility logic
│   │   └── streaming.py        ← streaming availability resolver
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             ← Pydantic models for users
│   │   ├── film.py             ← Pydantic models for film data
│   │   ├── taste.py            ← Pydantic models for taste profiles
│   │   └── recommendation.py   ← Pydantic models for recs
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── client.py           ← Supabase client init
│   │   └── queries.py          ← reusable DB query functions
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── prompts.py          ← all LLM prompt templates
│   │   ├── claude.py           ← Anthropic API wrapper
│   │   └── parser.py           ← parse + validate LLM JSON responses
│   │
│   └── utils/
│       ├── __init__.py
│       ├── cache.py            ← simple in-memory + Redis cache helpers
│       ├── rate_limiter.py     ← per-user request throttling
│       └── logger.py           ← structured logging setup
```

---

## Environment Variables

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_TMDB_IMAGE_BASE=https://image.tmdb.org/t/p/
```

### Backend (`backend/.env`)
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
TMDB_API_KEY=
TMDB_BEARER_TOKEN=
OMDB_API_KEY=
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000
```

---

## Key Architecture Rules

1. **Frontend never calls TMDB, Anthropic, or OpenAI directly.** All AI and third-party calls go through the backend. The frontend only calls the Cinerex backend API and Supabase directly (for auth only).

2. **All scraping runs server-side** in the backend. Never in the browser.

3. **Taste profiles are generated once and cached** in the database. They are updated incrementally when new watches are synced, not regenerated from scratch every time.

4. **TMDB metadata is cached locally** in the `films` table. Never call TMDB for the same film twice if it's already in the DB.

5. **Recommendations are not stored** — they are generated fresh per session. Caching recs defeats the freshness goal.

6. **All API responses use consistent envelope format:**
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

7. **All timestamps are UTC ISO 8601 strings** in the database and API responses.
