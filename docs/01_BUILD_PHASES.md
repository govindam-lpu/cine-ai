# Cinerex — Build Phases

Nine phases, 0 through 8. Build in order. Each phase has: **Goal**, a **Prompt** you can act on
directly, what to **Port** from `archive/`, what to **Build**, **Edge cases & contingencies** to
handle, **Tests** to write, and a **Definition of Done (DoD)**. A phase is complete only when its DoD
holds *and* its tests pass. Commit at each boundary. Update the checklist in `02_HANDOVER.md`.

Read `PLAN.md` first for the rationale behind all of this. The non-negotiables are in
`00_MASTER_PROMPT.md` — respect them in every phase.

Target repo shape when the build is done:

```
backend/                 FastAPI service (fresh)
  app/
    api/                 routers: health, ingest, profiles, recommendations
    core/                config, rate limiting, the generation queue
    db/                  session/engine (SQLite local ↔ Turso prod)
    models/              SQLAlchemy models
    schemas/             Pydantic request/response models
    services/            ingest, tmdb, evidence, ranker, writer
    prompts/             *.md prompt templates (the product; version them)
  tests/                 pytest, with fixtures/ (real export samples, TMDB stubs)
  main.py
frontend/                Next.js app (fresh; ports components from archive)
docs/                    these docs
archive/                 the old build, reference only — never imported at runtime
```

---

## Phase 0 — Scaffold & harness

**Goal:** Two empty-but-running apps, a test harness, and config that already knows about SQLite vs
Turso and local vs hosted — so no later phase has to retrofit it.

**Prompt:** Create fresh `backend/` (FastAPI) and `frontend/` (Next.js 14, TypeScript, Tailwind)
skeletons at the repo root. Wire configuration, database session, a health endpoint, and runnable
(empty) test suites on both sides. Port only configuration *patterns* from `archive/`, not features.

**Port from archive:**
- `archive/backend/app/core/config.py` — the pydantic-settings pattern for env loading (adapt: add
  `GROQ_API_KEY`, `WRITER_BACKEND=ollama|groq`, `OLLAMA_HOST`, `DATABASE_URL`, keep the TMDB keys).
- `archive/backend/app/db/session.py` — the SQLAlchemy engine/session pattern. Adapt so
  `DATABASE_URL` drives it: a local `sqlite:///./cinerex.db` by default, a Turso libSQL URL in prod.
- `archive/frontend/` — `tailwind.config.js`, `postcss.config.js`, `tsconfig.json`, and
  `src/app/globals.css` design tokens (keep the tokens; the design phase revisits them).

**Build:**
- `backend/main.py` with app factory, CORS (allow the frontend origin via env), and `GET /health`
  returning `{status, version}`.
- `backend/app/db/` engine + session dependency, database-agnostic (no PRAGMA, no SQLite-only SQL).
- `backend/requirements.txt`: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `pydantic-settings`,
  `requests`, `beautifulsoup4`, `python-multipart` (uploads), `fastembed`, `numpy`, `pytest`,
  `httpx` (test client). Add the Turso/libSQL SQLAlchemy dialect — **confirm the current package
  name and dialect string against Turso's docs.**
- `frontend/` via the Next App Router. `package.json` deps: only what's used —
  `next`, `react`, `react-dom`, `lucide-react`, `clsx`, and a test stack (`vitest`,
  `@testing-library/react`, `@playwright/test`). Do **not** re-add `recharts`, `@supabase/*`,
  `@radix-ui/*`, or `class-variance-authority` — the archive proved them dead weight.
- `.env.example` documenting every variable. Real `.env` stays gitignored (see `02_HANDOVER.md`).
- `docker-compose.yml` for local: backend + frontend. (The Space Dockerfile comes in Phase 8.)

**Edge cases & contingencies:**
- App must boot with **no** `GROQ_API_KEY` set (local dev uses Ollama) — config validation must not
  hard-fail on a missing production-only key.
- App must boot with **no** database file present — create tables on startup via `create_all` (v1
  has no migrations; document that resetting = delete the DB file).
- Missing TMDB keys must degrade gracefully later, not crash at import (mirror how `archive/tmdb.py`
  guards this).

**Tests:**
- `test_health.py` — `GET /health` returns 200 with the expected shape.
- `test_config.py` — settings load from env with correct defaults; absent optional keys don't raise.
- Frontend: `tsc --noEmit` clean; one trivial vitest test runs; `playwright` installed and its config
  present (no e2e specs yet).

**DoD:** `uvicorn` serves `/health`; `npm run dev` serves a placeholder page; `pytest` and the
frontend test commands both run green with the tests above. Committed.

---

## Phase 1 — Data model + ingestion

**Goal:** A real Letterboxd export goes in; enriched, TMDB-matched films come out and are stored,
behind an async job with progress. This is the foundation everything else reads from.

**Prompt:** Define the v1 data model, port the TMDB client and (for local dev) the scraper, and build
`ingest.py` — a parser for the Letterboxd export ZIP/CSVs — plus the upload endpoint and the async
enrichment job.

**Port from archive:**
- `archive/backend/app/services/tmdb.py` — **keep essentially as-is.** It does live search/details/
  credits with fuzzy title matching and graceful degradation. This is good code.
- `archive/backend/app/scrapers/letterboxd.py` — port for **local dev only**, exposed behind the
  `POST /sync` path. It carries the Cloudflare/RSS handling. Never the prod path.
- `archive/backend/app/utils/ratings.py` — star-glyph → float parsing, reusable for scraped data.
- `archive/backend/app/services/sync.py` — the async-job/progress *pattern* (adapt to the new model).

**Build:**
- **Models** (`app/models/`): `Profile` (handle PK, display_name, timestamps — see `PLAN.md` §1a),
  `Film` (tmdb_id+media_type unique, genres JSON, vote_count, runtime, director/crew, `embedding`
  column added in Phase 3), `WatchHistory` (profile→film, rating, watched_at, is_rewatch, review_text
  if present), `TasteProfile` (profile FK, `evidence_json`, `summary`, timestamps), `IngestJob`
  (status, step, counts, error), and keep `LetterboxdTmdbCache` from the archive (it amortizes TMDB
  matching across users).
- **`ingest.py`**: accept the Letterboxd export. The ZIP contains multiple CSVs; the ones that matter
  are `ratings.csv` / `diary.csv` / `watched.csv` (columns include Name, Year, Rating, Watched Date,
  Letterboxd URI, Rewatch — **the CSV carries no TMDB ID**, so titles route through `tmdb.py`).
  Parse defensively per Letterboxd's own rules (comma-delimited, quoted strings, ratings 0.5–5.0).
  De-duplicate across files (diary can repeat a film; keep the rated/most-recent instance).
- **Endpoints**: `POST /api/profiles/upload` (multipart; returns `{handle, job_id}`),
  `GET /api/profiles/{handle}/sync/{job_id}` (progress), and the local-dev
  `POST /api/profiles/{handle}/sync` (scrape). Both converge on the same enrichment job.
- **Enrichment job**: for each parsed film, resolve to TMDB (cache first), fetch details+credits,
  upsert `Film`, write `WatchHistory`. Async with progress steps: `parsing → enriching → complete`.

**Edge cases & contingencies:**
- **Not a real export:** wrong file type, a ZIP without the expected CSVs, a bare single CSV, empty
  file, or a CSV with headers only → friendly, specific 4xx, never a 500 or stack trace.
- **Encoding/format:** UTF-8 with BOM, quoted commas in titles, films with no rating (logged but
  unrated), 0.5-star increments, missing year, non-Latin titles.
- **TMDB match failures:** no result, multiple close results (use the existing fuzzy threshold),
  wrong-year match. Record unmatched films rather than dropping silently; surface a count.
- **Huge libraries** (1000+ films): the job must stream progress and not time out or exhaust memory;
  respect TMDB rate limits with the archive's backoff.
- **Duplicate/re-upload:** re-uploading for an existing handle should re-ingest cleanly
  (idempotent-ish: update, don't duplicate rows).
- **Someone else's export:** anonymous v1 has no ownership — accept it; it just produces that
  profile. (Noted, not a bug.)

**Tests:**
- Fixtures: a real (anonymized) export ZIP, a malformed ZIP, an empty CSV, a headers-only CSV, a CSV
  with quoted-comma titles and unrated rows. Commit these under `tests/fixtures/`.
- `test_ingest_parse.py` — each fixture parses to the expected film/rating set or the expected error.
- `test_enrich.py` — TMDB client mocked/stubbed at the HTTP layer; matched and unmatched paths;
  cache hit avoids a second call.
- `test_upload_endpoint.py` — happy path returns a job; bad upload returns the right 4xx.

**DoD:** Upload a real export → job runs → films enriched and stored → progress reports correctly →
unmatched films counted, not dropped. All fixtures tested. Committed.

---

## Phase 2 — Evidence layer

**Goal:** Honest, fast statistics that describe a viewer — the input the ranker and writer both
depend on. No model, no network.

**Prompt:** Build `evidence.py`: pure functions over a profile's rated films that produce a structured
`evidence_json`, plus the minimum-viable-profile gate.

**Port from archive:** `archive/backend/app/services/profile.py` — mine it for the *statistics that
were real* (genre/era counting, rating averages) and discard the parts pretending to be AI (the
f-string "summary", the magic-number "pretension score"). You are promoting honest stats, not keeping
fake ones.

**Build — compute per profile from rated films:**
- Genre affinity: mean rating per genre vs the user's personal baseline, weighted by count.
- Era affinity: mean rating per decade.
- Crew affinity: directors/cinematographers/composers rated above baseline, **with a minimum sample
  size** (e.g. ≥3 films) so one 5-star film doesn't crown someone.
- Contrarianism: correlation between user rating and TMDB `vote_average` (the honest "pretension"
  signal — a real coefficient).
- Obscurity preference: correlation between user rating and `log(vote_count)`.
- Patience: correlation between user rating and runtime.
- Rewatch signal: common traits of rewatched films.
- Recency drift: last-12-months genre/era distribution vs lifetime.
- Store each with its sample size / confidence so downstream can discount thin signals.
- **Min-viable-profile gate:** require ≥25 films with ≥15 rated (per `PLAN.md`). Below it, return a
  specific, friendly message; do not generate a low-quality profile.

**Edge cases & contingencies:**
- All films rated identically (zero variance) → correlations undefined; return neutral, not NaN/crash.
- Fewer than the gate → the gate fires with the exact counts in the message.
- Films missing genre/runtime/vote_count (TMDB gaps) → exclude from that signal, don't skew it.
- A single dominant genre → don't let it swamp; baseline-relative scoring handles this — test it.

**Tests:**
- `test_evidence.py` with hand-built film sets where the expected stats are known (a slow-burn lover,
  a contrarian, a mainstream-consensus viewer) → assert the signals point the right way.
- Degenerate inputs (identical ratings, empty, below-gate, missing fields) → no crash, sane output.
- The gate: 24 films / 14 rated fails with the right message; 25/15 passes.

**DoD:** `evidence_json` is produced for a real profile and the signals are legible and correct on the
hand-built cases; the gate behaves exactly. Committed.

---

## Phase 3 — Ranker

**Goal:** The product's core. Given the evidence and TMDB candidates, produce the top 8 films the user
hasn't seen — **with the structured reasons each one scored.** Measured, not vibes.

**Prompt:** Build `ranker.py`: embed films with `fastembed`, build a taste vector, pull and score TMDB
candidates, exclude watched films in code, return the top 8 each with the signals that fired. Add a
held-out evaluation.

**Build:**
- Embed `overview + genres + keywords` per film into a 384-dim vector via `fastembed`
  (`all-MiniLM-L6-v2`; **confirm the exact model id/API**). Cache on the `Film.embedding` column.
- Taste vector: rating-weighted mean of the user's high-rated film embeddings minus a weighted mean
  of low-rated ones.
- Candidates: TMDB `discover`, seeded by the evidence's top genres/eras/languages, ~60 films.
  **Filter `watched_ids` out in Python before scoring** — a hard invariant, never delegated.
- Score = cosine(candidate, taste vector) blended with evidence signals (vote_count vs obscurity
  preference, runtime vs patience, director in affinity list, …). Weights hand-set, then tuned.
- Return top 8, each carrying a `signals` bundle (which factors fired, how strongly) — this is what
  the writer consumes. The ranker explains itself; the model never guesses why a film was picked.

**Evaluate (build this, don't skip):** hold out 20% of the user's rated films, rank them among
decoys, and measure whether their 4.5-star films rank above their 2-star films (e.g. AUC or nDCG).
This number *is* the product quality. If it doesn't beat random by a clear margin, stop and fix the
scoring before moving on.

**Edge cases & contingencies:**
- `fastembed` output not matching the sentence-transformers reference (known risk) — sanity-check
  vectors early; if parity fails, fall back to `sentence-transformers` (heavier image, note it).
- Thin candidate pool (niche taste, obscure filters) → widen the discover query rather than return
  <8; log when the pool was widened.
- All candidates already watched → widen; never return watched films (test this invariant hard).
- Cold film with no overview/keywords → embed what exists or skip with a reason, don't crash.

**Tests:**
- `test_ranker_excludes_watched.py` — the hard invariant: no watched film ever appears. Property-style
  if possible.
- `test_taste_vector.py` — a user who loves genre X gets X-heavy candidates ranked up.
- `test_eval_beats_random.py` — the held-out metric clears the threshold on fixture profiles.
- Embedding cache: second run doesn't re-embed.

**DoD:** Top-8 recommendations produced for a real profile, watched films provably excluded, held-out
eval beats random by a clear margin, each rec carries its signal bundle. Committed.

---

## Phase 4 — Writer

**Goal:** Turn the ranker's structured signals into short, specific, second-person prose — the "why
this, for you." The only component that touches an LLM, and it does no reasoning.

**Prompt:** Build `writer.py`: a `Writer` protocol with `OllamaWriter` (local) and `GroqWriter`
(prod) implementations, selected by `WRITER_BACKEND`. Write the two prompt templates. Constrain and
validate output; fall back to a template on failure; stream reasons to the client.

**Build:**
- `Writer` protocol: `write_taste_summary(evidence) -> str` and
  `write_reason(evidence, film, signals) -> Reason`.
- `GroqWriter`: `llama-3.3-70b-versatile` via Groq's OpenAI-compatible API. **Confirm the current
  structured-output/JSON parameter.** Handle 429 (daily/RPM cap) explicitly.
- `OllamaWriter`: `llama3.2:3b-instruct-q4_K_M` on the local Ollama server; use its `format` param
  for JSON. Offline, unlimited — the prompt-iteration workhorse.
- Prompts in `app/prompts/taste_summary.md` and `app/prompts/reason.md` — not string literals.
  Second person, specific, grounded in the passed facts; explicitly instructed **not** to invent
  facts beyond the signals.
- Validate every response against a schema before it's stored or returned. On two failures, fall back
  to a **templated** sentence built from the same signals — degraded, never broken, never a trace.
- Streaming: reasons generate **one film at a time**, streamed to the browser as each completes.

**Edge cases & contingencies:**
- Malformed/non-JSON model output → schema validation catches it → retry once → template fallback.
- Groq 429 (rate/daily cap) → surface upward so Phase 5's capacity handling can show "at capacity",
  never a 500. Optionally fall back to the smaller Groq model for reasons.
- Ollama not running in local dev → clear, actionable error ("start Ollama / pull the model"), not a
  cryptic connection trace.
- Empty/degenerate signals (thin evidence) → the reason must not fabricate; prefer honest, plainer
  phrasing. (If reasons read generic, the fix is the ranker's evidence, not the prompt.)
- The two writers must produce the **same schema** so nothing downstream depends on which ran.

**Tests:**
- `test_writer_schema.py` — valid model output parses; malformed triggers retry then template.
- `test_writer_fallback.py` — forced failure yields the templated sentence, not an exception.
- `test_writer_protocol.py` — both implementations satisfy the protocol and return the same shape
  (Groq mocked at the HTTP layer; Ollama mocked or skipped in CI).
- A prompt-regression check: given a fixed signal bundle, the reason references the right facts.

**DoD:** Real, specific reasons generated for real recommendations via `OllamaWriter`; `GroqWriter`
verified against the live free tier at least once; fallback and rate-limit paths tested. Committed.

---

## Phase 5 — API surface, orchestration & guardrails

**Goal:** Wire the pipeline end to end behind the final endpoints, and add the protections a public,
no-auth, free-tier app must have before it can be reachable.

**Prompt:** Assemble upload → job → evidence → ranker → writer into the real endpoint surface, then
add rate limiting, the Groq daily-budget cap, a single-worker generation queue, capacity states, and
`noindex`.

**Build:**
- Final surface (per `PLAN.md` §1a):
  `POST /api/profiles/upload`, `GET /api/profiles/{handle}/sync/{job_id}`,
  `GET /api/profiles/{handle}` (taste profile, 404 if never ingested),
  `GET /api/profiles/{handle}/recommendations?mood=&limit=` (ranks fresh, streams reasons).
- Recommendations are generated **fresh per request** (never cached) and stream reasons as they land.
- **Rate limit** per handle and per IP (a lightweight in-process limiter is fine for v1).
- **Groq daily-budget cap:** count generations against the free-tier daily limit; at the ceiling,
  return a friendly "at capacity, back tomorrow" state — never an error.
- **Single-worker queue:** one ingest/generation at a time on a 2-vCPU box; others wait with an
  honest position indicator.
- `noindex` header on profile responses/pages (the URL exposes a generated inference — see
  `PLAN.md` Risks).

**Edge cases & contingencies:**
- Recommendations requested before ingest completes → clear "still building" state, not an empty list.
- Profile below the min-viable gate → the gate's friendly message, surfaced through the API.
- Concurrent uploads for the same handle → the queue serializes; no corruption.
- Cold start (Phase 8's Space sleeps) → first request may wait; the client shows "waking up".

**Tests:**
- `test_pipeline_e2e.py` — upload fixture → poll to complete → profile present → recommendations
  return 8, all unwatched, each with a reason. The whole chain, with TMDB and the writer stubbed.
- `test_rate_limit.py` and `test_capacity_cap.py` — limits and the daily cap produce the friendly
  states, not 500s.

**DoD:** A single automated test drives upload-to-recommendations end to end and passes; guardrails
demonstrably return graceful states. Committed.

---

## Phase 6 — Frontend (two screens, functional)

**Goal:** The real user journey in the browser — upload, watch the profile and recs appear, tweak,
share. Plain but complete. (Design polish is Phase 7.)

**Prompt:** Build the two screens against the Phase 5 API, porting the good components from `archive/`.
Wire upload, job polling, streaming recommendations, the mood filter, tweak/re-roll, and the share
URL. Delete the old multi-screen/nav/store patterns — they don't apply.

**Port from archive (these are prop-driven and good):**
`TasteDNACard`, `ToneRadarChart` (hand-rolled SVG — keep), `GenreBreakdown`, `CrewAffinities`,
`PretensionScore`, `TasteTimeline`, `RecommendationGrid`, `FilmCardFeature`, `FilmCardCompact`,
`ConfidenceBadge`, `StreamingBadge`, `MoodSelector`, `LoadingTypewriter`, the shared
`EmptyState`/`ErrorState`/`LoadingSpinner`. Adapt props to the new API shapes.

**Build:**
- `/` — the door: a single upload control (drag-drop the export ZIP) + an optional handle field, and
  honest copy. No feature-card scaffolding, no stale "coming soon".
- `/u/{handle}` — the product, one page: Taste DNA card (prose summary first, big), then the
  recommendations where **the reason is the card, not a caption**; the mood filter inline; tweak/
  re-roll controls; the URL is the share button.
- Ingest-in-progress state (reuse `LoadingTypewriter` + the archive's polling pattern).
- **No client-side persistence.** No zustand store, no localStorage — the handle is in the URL, the
  data is on the server. (Accounts/persistence are v1.1.)

**Edge cases & contingencies:**
- Upload rejected (bad file) → the friendly error from the API, inline, with a retry.
- Below-gate profile → the specific "log more films" message, not an empty page.
- Streaming reasons: render each as it arrives; a failed/late reason shows the template fallback, not
  a gap.
- Cold start / "waking up" and "at capacity" states rendered honestly.
- `noindex` on the profile route.

**Tests:**
- Component tests (vitest + testing-library) for the cards with real-shaped props, including empty/
  error states.
- `tsc --noEmit` clean.
- Playwright e2e: upload a fixture → profile renders → 8 recs with reasons → mood re-roll changes them
  → share URL loads the same profile. (Point at a seeded local backend.)

**DoD:** The full journey works in a real browser against the real backend; e2e passes. Committed.

---

## Phase 7 — Design pass

**Goal:** Make it look intentional, now that there's real content to design around.

**Prompt:** With the two screens functional and populated, do a deliberate visual design pass. Decide
the direction *against real content* — a real taste summary, real posters, real reasons — not in the
abstract.

**Reference:** `docs/DESIGN.md` (the prior visual identity) as a starting point, not a mandate. The
structural note from `PLAN.md`: this app has exactly one hero object (the Taste DNA card) and one
repeated object (the recommendation). Spend the design budget on those two; keep everything else
almost aggressively plain. If a fresh direction is wanted, propose 3–4 concrete options (palette,
type, layout) against the real screens and pick one — don't restyle blindly.

**Edge cases & contingencies:** dark/light legibility, long vs short taste summaries, missing posters,
very long film titles, mobile layout of the reason-cards, the loading/empty/error/at-capacity states
all styled (not just the happy path).

**Tests:** visual/interaction states covered by the existing component tests still pass; add snapshot
or visual checks if useful. No regressions to the e2e journey.

**DoD:** Both screens look considered and cohesive across states and viewports; the journey still
passes. Committed.

---

## Phase 8 — Deploy

**Goal:** Live, public, $0, always-on — no GPU, no residential IP.

**Prompt:** Deploy frontend to Vercel, backend to a Hugging Face Space (Docker), database to Turso,
prose to Groq. Configure env, handle the sleep/cold-start UX, and verify the real journey in
production.

**Build:**
- Backend `Dockerfile` for the Space (CPU; `fastembed` + FastAPI; confirm the model downloads at
  build or first run, not per request). Set `WRITER_BACKEND=groq` and `GROQ_API_KEY` as Space
  secrets; point `DATABASE_URL` at Turso.
- Frontend on Vercel, `NEXT_PUBLIC_API_URL` → the Space URL; CORS on the backend allows the Vercel
  origin.
- Turso database provisioned; confirm the app's tables create against it (agnostic ORM pays off here).
- Cold-start UX: the Space sleeps after ~48h idle → first hit waits ~30–60s; the frontend shows a
  "waking up" state rather than a dead spinner.

**Edge cases & contingencies:**
- Groq daily cap reached in production → the "at capacity" state is real and visible.
- Space memory: verify `fastembed` + the job fit the free box under a real 300+ film upload.
- Secrets never in the repo or client bundle; `.env` gitignored; keys only in platform secret stores.
- A real end-to-end upload from a clean browser, on the deployed URLs, actually works.

**Tests:** a documented manual smoke test (upload → profile → recs → tweak → share) on the live URLs,
plus the automated suites green in CI.

**DoD:** A stranger can use the deployed site end to end, free, with no account and no scraping.
Committed and tagged (`v1.0`).

---

## After v1 — v1.1 backlog (do not build in v1)

Accounts (persistence only; magic-link or OAuth, **no passwords**), anti-recommendations, and the
wild-card pick. All strictly additive on top of the anonymous core — see `PLAN.md`. The archived
`AntiRecCard`/`WildCardCard` components and the old `MASTER_PROMPT.md` feature list are the reference.
