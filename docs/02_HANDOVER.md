# Cinerex — Handover

The state of the world for whoever (a fresh session, or you) picks this up. Pair it with
`00_MASTER_PROMPT.md` (the constraints and method) and `01_BUILD_PHASES.md` (the work).

---

## Where things stand right now

- **Planning is done.** Architecture, constraints, and product shape are decided and recorded in
  `docs/PLAN.md`. There are **no open architecture questions.**
- **The old build is archived, intact, under `archive/`.** Nothing at the repo root runs yet — the
  fresh `backend/` and `frontend/` are built by Phase 0. This is deliberate: we start fresh and
  cherry-pick from the archive, because the requirements changed.
- **Phase 0 is done (2026-07-11).** Fresh `backend/` (FastAPI) and `frontend/` (Next.js 14) boot;
  `GET /health` returns `{status, version}`; `pytest` (4) and `vitest` (3) + `tsc --noEmit` are green;
  the production `next build` compiles. `.venv` was recreated (the old one had no pip).
- **Phase 1 is done (2026-07-11).** v1 data model (Profile/Film/WatchHistory/TasteProfile/IngestJob/
  LetterboxdTmdbCache); `ingest.py` parses the export ZIP/CSV (dedupe across ratings/diary/watched/
  reviews, BOM/quoted-comma/non-Latin/missing-year handling, friendly IngestError codes); `enrich.py`
  resolves films via TMDB (cache-first, one `append_to_response=credits,keywords` call, crew+keyword
  capture) behind an async job with progress; `POST /api/profiles/upload`, the job-progress endpoint,
  and the local-dev `POST /api/profiles/{handle}/sync` scrape. **44 pytest pass**; verified live
  against real TMDB (7/7 fixture films matched, crew/keywords/genres correct).
- **Phase 2 is done (2026-07-11).** `evidence.py` — pure-Python statistics (genre/era/crew affinity
  baseline-relative, contrarianism = corr(rating, vote_average), obscurity = corr(rating,
  log10 vote_count), patience = corr(rating, runtime), rewatch signal, recency drift, discovery
  seeds), each with sample size + confidence; correlations return None (not NaN) on zero variance.
  Min-viable gate (≥25 films, ≥15 rated) with a counts-in-the-message error. Pure core + thin DB
  adapters (load_watches/store_evidence). **58 pytest pass**; validated on a real 28-film library
  via live TMDB — signals are legible (e.g. obscurity −0.63, Tarkovsky surfaced at n=5). NOT yet
  wired into the ingest job — the "analyzing" step lands in Phase 5 orchestration.
- **Phase 3 is done (2026-07-11).** `embeddings.py` (fastembed all-MiniLM-L6-v2, 384-dim, unit-norm;
  verified sane — no sentence-transformers fallback needed) + `ranker.py`: taste vector
  (rating-weighted mean of embeddings, baseline-centered), TMDB discovery seeded by evidence, watched
  filtered in Python (hard invariant), score = cosine + evidence tilts (director/genre/era/obscurity/
  patience), top-8 each with a `signals` bundle. Held-out eval (pairwise AUC over ≥1-star-gap pairs).
  `Film.embedding` column added (JSON; DB reset picks it up). **65 pytest pass** (watched-exclusion
  property test, real-embedding taste vector, AUC eval, embedding cache). Tuned against real output:
  discovery sorts by vote_average (not popularity) with no language hard-filter, seeds blend
  representation+affinity — arthouse viewer now gets Amadeus/Cinema Paradiso/Night and Fog (AUC 0.89,
  was 0.58 with popularity sort). Not yet wired to an endpoint — that's Phase 5.
- **Phase 4 is code-complete (2026-07-11), live verification pending.** `writer.py`: `Writer` protocol
  with `GroqWriter` (llama-3.3-70b-versatile, JSON-object mode — 70B doesn't support Groq strict
  json_schema, so we validate with Pydantic) and `OllamaWriter` (llama3.2:3b, `format:json`), chosen
  by `WRITER_BACKEND`. Prompts in `app/prompts/*.md`. Retry once on bad JSON → **template fallback**
  built from the same signals (real, specific prose, no LLM — verified on the real arthouse recs).
  429 → `WriterRateLimited` (for Phase 5 capacity); backend-unreachable → `WriterUnavailable`
  (actionable). **82 pytest pass** (schema/retry/fallback/protocol-parity/429/unavailable).
  **BLOCKED on live check:** the DoD wants one real GroqWriter call (needs a free `GROQ_API_KEY` —
  I can't create the account) and/or OllamaWriter (needs local Ollama). Neither is available in this
  environment. Everything else is done and tested; Phase 5 can be built against the writer meanwhile.
- **Phase 5 is done (2026-07-11).** Full endpoint surface wired end to end: `run_full_ingest`
  (enrich → analyze = evidence + written summary → store) on a single-worker queue; `GET
  /api/profiles/{handle}` (discriminated states: not_found 404 / building / needs_more_films /
  failed / ready); `GET /api/profiles/{handle}/recommendations` ranks fresh and streams reasons as
  SSE, one film at a time. Guardrails: per-IP + per-handle rate limits (`ratelimit.py`), Groq daily
  budget with a friendly at-capacity state (`budget.py`, only metered when WRITER_BACKEND=groq),
  single-worker queue with position (`queue.py`), `noindex` on profile responses. Below-gate
  profiles surface the friendly message; recs-before-ready return "building", never an empty stream.
  **92 pytest pass** incl. a full upload→profile→8-recs e2e (TMDB + writer stubbed), rate-limit 429s,
  and the capacity path (templates + at_capacity flag, never a 500). NOTE: the app degrades to
  template prose when no LLM is reachable, so the whole journey works locally without Ollama/Groq —
  which is what lets Phase 6's e2e run against a seeded backend. Phase 6 (frontend) next.

Repo root today:

```
archive/     the complete old build — reference only, never imported at runtime
docs/        PLAN.md, DESIGN.md, PRIVACY_LEGAL.md, and these three handoff docs
README.md    project intro (rewrite/keep current as the fresh build lands)
.env         real secrets (gitignored) — TMDB keys live here
```

---

## The archive — what to reuse, what to ignore

`archive/` is a faithful copy of the prior build. It runs, it has real edge-case handling, and it's
the reference for both good code and cautionary tales.

**Port these (they're genuinely good):**
- `archive/backend/app/scrapers/letterboxd.py` — `requests`+BS4 scraper with Cloudflare detection,
  backoff, and an RSS fallback that carries TMDB IDs. **Local-dev ingestion only** (Cloudflare 403s
  datacenter IPs — the deployed path is CSV upload).
- `archive/backend/app/services/tmdb.py` — live TMDB search/details/credits with fuzzy title
  matching and graceful degradation. Keep essentially as-is.
- `archive/backend/app/utils/ratings.py` — star-glyph → float parsing.
- `archive/backend/app/services/sync.py` — the async-job + progress pattern (adapt to the new model).
- `archive/backend/app/services/profile.py` — mine for the *real* statistics only; discard the
  f-string "summary" and magic-number "pretension score".
- Frontend components (prop-driven, reusable — adapt props to new API shapes):
  `taste/{TasteDNACard, ToneRadarChart, GenreBreakdown, CrewAffinities, PretensionScore,
  TasteTimeline}`, `recommendations/{RecommendationGrid, MoodSelector, ConfidenceBadge,
  StreamingBadge}`, `cards/{FilmCardFeature, FilmCardCompact}`, `onboarding/LoadingTypewriter`, and
  `shared/{EmptyState, ErrorState, LoadingSpinner}`.
- Design tokens in `archive/frontend/src/app/globals.css` and `tailwind.config.js`.
- `archive/frontend/src/components/{cards/AntiRecCard, recommendations/WildCardCard}.tsx` — **v1.1
  reference**, not v1.

**Ignore these (the reason for the rebuild):**
- The heuristic taste profile and recommendation "AI" (`profile.py` summary, `recommendations.py`) —
  replaced by evidence + ranker + writer.
- Dead scaffolding the old build carried: empty routers, the Supabase stub (`lib/supabase.ts` was
  literally `export const supabase = null`), the multi-screen sidebar/bottom-nav, the zustand
  store, and the four unused npm deps (`recharts`, `@supabase/*`, `@radix-ui/react-slot`,
  `class-variance-authority`).
- `archive/docs-legacy/MASTER_PROMPT.md` — the aspirational 24-feature vision. Useful as a *backlog*,
  not a spec. `archive/docs-legacy/PRODUCT_DECISIONS.md` — old business rules, largely superseded by
  `PLAN.md`.

The pristine original is also in git history (commit `32cf0d8`) if you ever need a file exactly as it
was before the archive move.

---

## Secrets & environment

**Never commit secrets.** `.gitignore` ignores `.env` at every depth (verified), so `.env` and
`archive/backend/.env` are safe. Keys live only in local `.env` files and, in production, in platform
secret stores.

| Variable | For | Where it is / how to get it |
|---|---|---|
| `TMDB_API_KEY`, `TMDB_BEARER_TOKEN` | TMDB enrichment | Already in root `.env` (and `archive/backend/.env`). Reuse them. |
| `DATABASE_URL` | DB | Local: `sqlite:///./cinerex.db` (default). Prod: the Turso libSQL URL (Phase 8). |
| `WRITER_BACKEND` | pick the writer | `ollama` locally, `groq` in prod. |
| `GROQ_API_KEY` | prod prose | Free, no card — create at console.groq.com. Not needed for local dev. |
| `OLLAMA_HOST` | local prose | Default `http://localhost:11434`. |
| `NEXT_PUBLIC_API_URL` | frontend → backend | Local `http://127.0.0.1:8000`; prod the Space URL. |

**Local-dev prerequisites for the writer (Phase 4+):** install [Ollama](https://ollama.com) and
`ollama pull llama3.2:3b-instruct-q4_K_M` (~2 GB, fits a 4 GB GPU). Until Phase 4 you don't need it.

A Python virtualenv exists at `.venv` (root); reuse or recreate it for the fresh backend.

---

## How to run & test (fill in as phases land)

Local, once Phase 0 exists:

```
# backend
cd backend && uvicorn main:app --reload         # http://127.0.0.1:8000
pytest                                            # backend tests

# frontend
cd frontend && npm run dev                        # http://localhost:3000
npm run test        # vitest
npx tsc --noEmit    # types
npx playwright test # e2e (once Phase 6 exists)

# both, containerized
docker compose up --build
```

Reset the local database: delete the SQLite file and restart (v1 has no migrations; tables
self-create on startup).

---

## Progress checklist — the building session keeps this current

Mark a phase done only when its Definition of Done in `01_BUILD_PHASES.md` holds **and** its tests
pass. Commit at each boundary.

- [x] **Phase 0** — Scaffold & harness (both apps boot, `/health`, tests run) — done 2026-07-11
- [x] **Phase 1** — Data model + ingestion (upload real export → enriched films stored) — done 2026-07-11
- [x] **Phase 2** — Evidence layer (statistics + min-profile gate) — done 2026-07-11
- [x] **Phase 3** — Ranker (top-8, watched excluded, held-out eval beats random) — done 2026-07-11
- [~] **Phase 4** — Writer (Ollama + Groq behind one protocol, fallback works) — CODE COMPLETE +
  82 tests 2026-07-11; **live LLM verification pending a GROQ_API_KEY or local Ollama** (see note)
- [x] **Phase 5** — API + orchestration + guardrails (e2e upload→recs; rate/capacity states) — done 2026-07-11
- [ ] **Phase 6** — Frontend (two screens, full journey, e2e passes)
- [ ] **Phase 7** — Design pass (cohesive across states/viewports)
- [ ] **Phase 8** — Deploy (Vercel + HF Space + Turso + Groq; live, free, working)

---

## Verified facts & things still to confirm at build time

**Verified during planning (2026-07):**
- Letterboxd data export is **free** (no Pro) — upload onboarding is frictionless.
- The Letterboxd **API beta is closed** — no username-ingestion path exists; CSV upload is permanent.
- Cloudflare **403s datacenter IPs** on Letterboxd (films page *and* RSS) — scraping is local-only.
- Groq free tier serves `llama-3.3-70b-versatile`, no card, ~1,000 req/day (≈110 profiles/day).
- Turso free tier: SQLite-compatible, 5 GB, 500M row-reads/mo.
- Hugging Face Space free tier: 2 vCPU / 16 GB, Docker, sleeps after ~48h idle.

**Confirm against current official docs when you reach them (don't trust memory):** the `fastembed`
model id and API; the Turso/libSQL SQLAlchemy dialect + connection string; Groq's structured-output
parameter and current limits; Ollama's `format` parameter. Getting these from the live docs at build
time is part of the job.

**Confirmed during Phase 0 (2026-07-11):**
- Turso/libSQL dialect: package `sqlalchemy-libsql` (v0.2.0), dialect string `sqlite+libsql://`,
  URL form `sqlite+libsql://<db>-<org>.turso.io/?authToken=<token>&secure=true`. **Linux/macOS wheels
  only — no Windows.** So it's gated in `requirements.txt` with `; platform_system != "Windows"`:
  local Windows dev uses plain SQLite (doesn't need it), the Linux Space image installs it. Phase 8
  will finalize the Turso connect args.
- `fastembed` 0.8.0 installs clean on Windows/Py3.12 (pulls `onnxruntime`, no PyTorch). Exact model
  id/vector parity still to verify in Phase 3, per the plan.

**Deferred to Phase 8 (deploy) — Next.js security audit:** `npm audit` flags a rolling advisory range
that no Next.js 14.2.x release clears (only Next 16+, a breaking major that would move off the
specified Next 14 stack). Pinned to the latest patched **14.2.35**. Residual advisories are largely
inapplicable to this app (App Router; no i18n, middleware, remote image optimization, or WS upgrades;
backend is a separate service) and it isn't deployed yet. Re-evaluate the real deployed surface at
Phase 8 before going public.

---

## Not decided (deliberately) / open

- **Visual design direction** — Phase 7, decided against real content. `DESIGN.md` is a starting
  reference, not a mandate.
- **v1.1 specifics** — accounts (magic-link vs OAuth), anti-recs, wild card. Out of v1 scope; shape
  is in `PLAN.md`.
- **Privacy posture of public profile URLs** — the URL exposes a *generated inference* about a
  person (see `PLAN.md` Risks and `PRIVACY_LEGAL.md`). `noindex` is the v1 minimum; revisit if the
  product goes wide.

---

## If you're resuming mid-build

1. Read `PLAN.md`, then `01_BUILD_PHASES.md`.
2. Check this checklist and `git log` to see the last completed phase.
3. Run the test suites to confirm the last phase is actually green.
4. Continue at the next unchecked phase. Don't skip; don't leave stubs.
