# Cinerex — v1 Rebuild Plan

**Status:** Active. This document supersedes `MASTER_PROMPT.md`, `PRODUCT_DECISIONS.md`, and the
rest of `docs/` wherever they disagree. Those describe a product that was never built.

**Date:** 2026-07-10

---

## What Cinerex is, in one sentence

You give us your Letterboxd history — upload your export in the deployed app, or let it scrape when
running locally. We work out who you are as a viewer from the patterns in your ratings, and hand you
a handful of films with a real reason attached to each one.

No account. No password. No onboarding wizard.

---

## What we're actually correcting

The repository today contains a small, working vertical slice buried under the spec for a
24-feature platform. Three things are true at once:

1. **The scraper and the TMDB integration are good.** Real code, real edge cases handled
   (Cloudflare detection, private profiles, RSS fallback that carries TMDB IDs). Keep them.
2. **There is no AI in this AI product.** Zero Anthropic or OpenAI calls exist anywhere. The
   "taste profile" is an f-string template; the recommendations are hardcoded genre maps and
   magic-number arithmetic. This is the whole gap.
3. **The no-login flow already exists** — there is no auth at all, which is exactly right for v1.
   We formalize that: anonymous upload in v1, with accounts added deliberately in v1.1 for
   persistence — not bolted on now.

So this is not a rewrite. It's a demolition, one new layer, and a new face.

---

## The four decisions

| Decision | Choice |
|---|---|
| Rebuild scope | Keep `letterboxd.py` and `tmdb.py`. Gut everything else. |
| Identity | Anonymous in v1 (upload → recs, session-only). Accounts in v1.1 for persistence. Line drawn at persistence, not features. |
| v1 features | Taste profile + recommendations with real reasons; Taste DNA card; mood filter. |
| Reasoning | Statistics and embeddings do the thinking, in code. An LLM writes only the prose. **$0 either way.** |
| Ingestion | **CSV/ZIP upload** is the public entry path. The scraper stays for local development. |
| Deployment | Frontend on Vercel, backend on Hugging Face Spaces, DB on Turso, prose from Groq. All free. |

**Explicitly cut from v1:** anti-recommendations, wild card picks, Serializd/TV, watchlist ranker,
compatibility mode, film twin, blind spots, prediction game, thematic universe, taste evolution,
streaming availability filter, pgvector (a vector DB — embeddings live in memory instead), Supabase,
Trakt.

**Accounts are deferred to v1.1, not cut.** v1 is fully anonymous: upload → profile → recs → tweaks,
all session-only. v1.1 adds accounts whose *only* job is persistence — save your profile, keep your
tweaks, skip re-uploading, track predicted-vs-actual ratings over time. The free/account line is
drawn at **persistence, not features**: everything works anonymously; the account *remembers* it,
it doesn't *unlock* it. No passwords — magic link or OAuth. Anti-recs and the wild card land
alongside accounts in v1.1; both are the same LLM call with a different prompt.

---

## Naming

Three names are in play: the repo folder is `CineAI`, the frontend says `Cinerex`, the stale docs
say `CinematicAI`. **Standardize on Cinerex.** The frontend already uses it and the domain reads
better. Rename the repo folder when convenient; it isn't urgent.

---

## Architecture after the rebuild

```
Browser
  │
  │  upload export  /  GET /u/{username}
  ▼
Next.js (Vercel)  ──HTTP──►  FastAPI (Hugging Face Space)
                               │
                               ├─ ingest.py       CSV/ZIP parser            [NEW]  ← public entry
                               ├─ letterboxd.py   requests + BS4 + RSS      [KEPT] ← local dev only
                               ├─ tmdb.py         search / details / credits[KEPT]
                               │
                               ├─ evidence.py     statistics over history   [NEW]  ─┐
                               ├─ ranker.py       fastembed + scoring        [NEW]  ─┤ the thinking
                               ├─ writer.py       Writer protocol, prose only[NEW]  ─┘
                               │                    ├─ OllamaWriter  (local dev)
                               │                    └─ GroqWriter    (production)
                               └─ Turso (libSQL)
```

**The load-bearing idea: the model never decides anything.** Ranking a film against a taste profile
is arithmetic on vectors. Deciding that someone is a contrarian is a correlation coefficient.
Neither needs a language model, and neither should pay for one. What a language model is uniquely
good at is turning `{user_slow_burn_avg: 4.3, film_is_slow_burn: true, director_avg: 4.5}` into a
sentence a human wants to read.

So the pipeline computes evidence in Python, ranks with embeddings, and hands the top eight
candidates — each with its own bundle of supporting facts — to a model whose only instruction is
*write two sentences using these facts*. That job is easy. "Reason about this person's soul from 60
films" is not — and we never ask it to.

This also resurrects embeddings, which an earlier draft of this plan cut. They were dead weight when
an LLM did the ranking. Now that nothing else does semantic matching, they're the core of it — and
run on CPU, so they cost nothing on any free host.

No Postgres. No pgvector — a few thousand float vectors fit in memory and `numpy` does cosine
similarity faster than a database round-trip.

---

## Deployment — the whole stack, decided

Everything below is free, always-on, and needs no GPU and no residential IP. This is the section to
re-read whenever "how does this actually run in the world" comes up.

| Layer | Choice | Why it's free and why it works |
|---|---|---|
| Frontend | **Vercel** (Hobby) | Static Next.js, generous free tier. |
| Backend | **Hugging Face Space** (Docker, 2 vCPU / 16 GB) | No card. Roomy enough for `fastembed` + FastAPI. Sleeps after 48h idle → first visit after a long gap eats a ~30–60s cold start. Fine for low, bursty traffic. |
| Database | **Turso** (libSQL) | SQLite-compatible, so it's near-drop-in for the existing SQLAlchemy code. Free tier: 5 GB, 500M row-reads/mo. |
| Prose model | **Groq** — `llama-3.3-70b-versatile` | No card, no per-token charge. 30 req/min, 1,000 req/day free. Nine generations per profile → ~110 full profiles/day. A 70B writes *better* prose than any model that fits a 4 GB card. |
| Embeddings | **fastembed** (ONNX, CPU) | No PyTorch → ~200 MB install instead of ~2 GB. Runs on the free CPU box. |
| Ingestion | **CSV/ZIP upload** | Immune to Cloudflare because there's no scraping. Real-time, works from any host. |

**Why not just scrape from the server?** Because it doesn't work. Letterboxd is behind Cloudflare,
and Cloudflare distrusts datacenter IPs by default. Verified 2026-07-11: a datacenter IP was
**403'd on both the films page and the RSS feed**, not just the HTML help pages. Scraping is a
residential-IP capability, which is why `letterboxd.py` stays useful for *local* development (your
home IP) but cannot be the public ingestion path. The public path is upload.

**Three things this obligates us to get right, and they're all cheap:**

1. **`ingest.py` is a first-class module, not a fallback.** The Letterboxd export is a ZIP of CSVs;
   `diary.csv` / `ratings.csv` carry title, year, rating, watched-date, and a rewatch flag — but
   **no TMDB IDs.** So parsing feeds straight into the existing `tmdb.py` title-matching path, the
   same enrichment the scraper already used. Nothing new there; the cache helps across users.
2. **Keep the ORM database-agnostic.** No SQLite-specific SQL, no raw `PRAGMA`. Then Turso in
   production and a local SQLite file in development are one connection-string apart.
3. **The `Writer` protocol is what makes the whole thing portable.** `OllamaWriter` for offline
   local dev, `GroqWriter` for production, selected by an environment variable. Neither costs money.

**Both open questions are now resolved (confirmed 2026-07-11):**

- **The export is free.** No Pro required — anyone can export their Letterboxd data from settings, so
  the "upload your export" onboarding is frictionless for every user, not just paying ones.
- **The official API is closed.** Letterboxd is not granting new API access, so there is no
  legitimate "type-a-username" path from a datacenter on any timeline we can plan around. **CSV
  upload is the permanent public ingestion path, not a stopgap.** If that ever changes, the scraper
  and a username entry point are still in the tree to switch back on.

---

## Phase 0 — Demolition

Delete first. Every line removed here is a line nobody has to reason about again. Everything is
recoverable from git history.

**Docs**
- `docs/cinematic_ai_design.md`, `docs/cinematic_ai_master_prompt.md` — byte-identical copies of
  `DESIGN.md` / `MASTER_PROMPT.md` with the old product name swapped in.
- `docs/DATABASE_SCHEMA.md`, `docs/API_CONTRACT.md` — describe a Supabase schema and endpoint set
  that does not exist. Rewrite as short, accurate files at the end of Phase 1, or delete.
- `docs/SCRAPER_SPEC.md` — describes Playwright. The scraper uses requests + BeautifulSoup.

**Backend**
- `app/api/compatibility.py`, `app/api/predictions.py`, `app/api/watchlist.py` — three lines each,
  an empty `APIRouter()`, mounted nowhere.
- `app/scrapers/serializd.py` — a four-line stub, never imported.
- `app/schemas/users.py` → `PatchUserRequest` — no PATCH endpoint exists.
- `app/models/entities.py` → the `Watchlist`, `StreamingService`, and `SerializdProfile` tables.
  Watchlist is never read or written. StreamingService is read once and never populated, which is
  why `"streaming": []` is hardcoded in the recommendations response.
- `_genre_stats` is implemented twice, near-identically, in `profile.py` and
  `recommendations.py`. Both are about to be replaced anyway.

**Frontend**
- `src/app/compatibility/`, `src/app/twin/`, `src/app/watchlist/` — honest "not built" shells.
  `/twin` isn't even linked from either nav.
- `src/hooks/useCompatibility.ts`, `src/hooks/useWatchlist.ts` — stubs that return a message string.
- `src/lib/supabase.ts` — the entire file is `export const supabase = null`.
- `src/components/layout/Sidebar.tsx`, `src/components/layout/BottomNav.tsx` — v1 has two screens.
  Navigation between two screens is a link.
- `src/components/cards/AntiRecCard.tsx`, `src/components/recommendations/WildCardCard.tsx` — cut
  from v1 scope. Git remembers them.
- Four dead dependencies: `recharts` (the radar chart is hand-rolled SVG), `@supabase/supabase-js`,
  `@radix-ui/react-slot` and `class-variance-authority` (shadcn primitives; shadcn is not installed
  — there is no `components.json` and no `components/ui/`).

**Database**
- Delete `backend/cine_ai.db` and let `create_all` rebuild it. It holds one test user. There is no
  migration to write, and no Alembic to set up. Take the free lunch.

---

## Phase 1 — Backend: identity, then the LLM layer

### 1a. Identity — anonymous now, owned later

Today a user is an opaque UUID with no ownership check. The switch to CSV upload changes the identity
question in a way worth stating plainly: **the export is about your films, not you — it carries no
username.** So there is nothing to key on automatically, and "username = identity" (an earlier
decision) quietly stops holding.

**v1 (anonymous).** On upload the user optionally types a handle; absent that, generate a slug. The
profile is served at `/u/{handle}`, public, `noindex`, no ownership — a public inference from data
the user handed us. Two people uploading the same export get the same profile; fine for anonymous.

**v1.1 (accounts).** An account (email via magic link, or OAuth) becomes the durable identity and the
owner of a saved profile; the handle demotes to a display label. Persistence, prediction tracking,
and saved tweaks all hang off the account.

For v1 the profile table is deliberately thin and un-authenticated:

```python
class Profile(Base):
    __tablename__ = "profiles"
    handle         = Column(String, primary_key=True)   # typed or generated; a label, not a login
    display_name   = Column(String)
    created_at     = Column(DateTime)
    last_ingest_at = Column(DateTime)
```

No email, no password, no UUID. Accounts in v1.1 add an `accounts` table *alongside* this one, not a
rewrite of it.

New surface, replacing everything in `app/api/`:

```
GET   /api/health
POST  /api/profiles/upload                       multipart CSV/ZIP → 202, returns {username, job_id}
POST  /api/profiles/{username}/sync              local-dev only: scrape → 202, returns job_id
GET   /api/profiles/{username}/sync/{job_id}     parsing | enriching | analyzing | complete | failed
GET   /api/profiles/{username}                   → taste profile, 404 if never ingested
GET   /api/profiles/{username}/recommendations   → ?mood=&limit=
```

`upload` is the public entry point; `sync` is the same pipeline fed by the scraper and only wired up
in local development (see Deployment). Both converge on the same job → enrich → analyze flow after
the first step; the only difference is where the raw film list comes from.

**Enforce the minimum-viable-profile gate**, which the spec mandates and the code has never
checked: 25 films logged, at least 15 with a rating. Below that, return a friendly, specific error
rather than generating a bad profile. The current code uses an undocumented threshold of 10 films,
in one place, for recommendations only.

### 1b. The evidence layer — `app/services/evidence.py`

Pure Python, no model, no network. This is where the existing `profile.py` heuristics get promoted
from "fake AI" to what they actually are: honest descriptive statistics. They were never bad code —
they were mislabeled.

Compute, per user, from their rated films:

- Genre affinity — mean rating per genre, weighted by count, versus their personal baseline.
- Era affinity — mean rating per decade.
- Crew affinity — directors, cinematographers, composers whose films they rate above their baseline,
  with a minimum sample size so one 5-star film doesn't crown a director.
- **Contrarianism** — the correlation between their rating and TMDB's `vote_average`. Negative
  correlation means they systematically disagree with the crowd. This is the honest version of the
  "pretension score," and it's a real number rather than a magic constant.
- **Obscurity preference** — correlation between their rating and `log(vote_count)`.
- **Patience** — correlation between their rating and runtime.
- Rewatch signal — what the films they rewatch have in common.
- Recency drift — last-12-months genre/era distribution versus lifetime baseline.

Every one of these is a number with a confidence interval, computed in milliseconds, for free. Store
the whole bundle as `taste_profiles.evidence_json`.

### 1c. The ranker — `app/services/ranker.py`

Content-based, embedding-driven, CPU-only.

Use **`fastembed`** with **`all-MiniLM-L6-v2`** — 384-dim output, runs through `onnxruntime` with
**no PyTorch dependency**, which keeps the deployed image around 200 MB instead of ~2 GB and matters
directly for fitting a free Hugging Face Space. It embeds sixty film overviews in well under a second
on CPU. (Caveat to check on first use: there are reports that fastembed's MiniLM output doesn't
*exactly* match the `sentence-transformers` reference — verify the vectors are sane before tuning
weights against them. If parity is a problem, `sentence-transformers` is the fallback at the cost of
the heavier image.)

1. Embed each film's `overview + genres + keywords` into a 384-dim vector. Cache it on the `films`
   row; it never changes.
2. Build the **taste vector**: a rating-weighted mean of the embeddings of the user's highly-rated
   films, minus a weighted mean of their lowly-rated ones. Their positive space, with their negative
   space subtracted out.
3. Pull 60 candidates from TMDB `discover`, seeded by the evidence layer's top genres, eras, and
   languages. **Filter `watched_ids` out in Python**, before scoring — never delegate a hard
   constraint you can enforce yourself.
4. Score each candidate: cosine similarity to the taste vector, blended with the evidence signals
   (does its vote count match their obscurity preference? its runtime their patience? its director
   in their affinity list?). Weights start hand-set and get tuned against held-out ratings.
5. Take the top 8. For each, emit not just a score but the **reasons it scored**: which signals fired
   and how strongly. That bundle is what the writer consumes.

Step 5 is the important one. The ranker doesn't just rank — it explains itself in structured form.
The language model never has to guess why a film was picked, because the ranker already knows.

**Evaluate it.** Hold out 20% of the user's rated films, rank them among decoys, and measure whether
the model puts their 4.5-star films above their 2-star films. That number is the product. Track it.

### 1d. The writer — `app/services/writer.py`

The only component that touches a language model, and it does no reasoning. It's a `Writer` protocol
with two implementations chosen by an environment variable — this indirection is what lets the same
codebase run free-and-offline on your machine and free-and-hosted in production.

```python
class Writer(Protocol):
    def write_taste_summary(self, evidence: Evidence) -> str: ...
    def write_reason(self, evidence: Evidence, film: Film, signals: Signals) -> Reason: ...
```

**`GroqWriter` — production.** Groq's free tier serves `llama-3.3-70b-versatile` with no card and no
per-token charge, at 30 req/min and 1,000 req/day. The API is OpenAI-compatible, so the adapter is a
few lines. Nine generations per profile (one summary + eight reasons) means the daily cap is roughly
**110 full profiles/day** — plenty for launch, and the binding constraint to watch, not dollars. A
70B model also writes markedly better prose than anything that would fit a 4 GB local card, so
production is the *higher*-quality path here, not the compromise.

**`OllamaWriter` — local development.** [Ollama](https://ollama.com) running
`llama3.2:3b-instruct-q4_K_M` (~2.0 GB, fits inside the 1650 Ti's 4 GB VRAM). Offline, unlimited, no
rate limit — the right thing for iterating on prompts without spending the daily Groq budget. Prose
is flatter than the 70B, but for wiring and prompt-shaping that's irrelevant.

Two jobs, identical across both implementations:

**`write_taste_summary(evidence)`** — one paragraph, second person, from the statistics. Once per
ingest.

**`write_reason(evidence, film, signals)`** — two sentences, second person, citing the specific
signals that fired. Eight per recommendation request, **one film at a time**, streamed to the browser
as each completes so the page fills progressively instead of showing one long spinner.

Constrain output to a JSON schema (Groq and Ollama both support structured output) and validate every
response before it reaches the database or the browser. If a generation fails twice, fall back to a
templated sentence built from the same signals — degraded, never broken, never a stack trace.

Keep the prompts in `app/prompts/*.md`, not in Python string literals. They are the product; they'll
be edited far more often than the code around them, and they should diff cleanly.

### 1e. Capacity and abuse

No paid API means no surprise bill — but a public upload endpoint with no auth still has an abuse
surface. It's now *someone else's* free tier (Groq's daily cap, the Space's CPU) rather than your
GPU, but the same discipline applies.

Three mitigations, all cheap, all mandatory before this is publicly reachable:

1. **Profiles generate only on explicit user action** — an upload, or a "build this profile?" click.
   Nothing kicks off enrichment and nine generations on a bare page view.
2. **Rate limit** per username and per IP, and **cap total generations against the Groq daily
   budget** — when the day's ~110-profile allowance is spent, show a friendly "at capacity, back
   tomorrow" state, never a 500.
3. **A single-worker job queue.** One ingest at a time on a 2-vCPU Space; concurrent requests wait in
   line with an honest position indicator rather than thrashing the box.

**The cold-start caveat:** the Hugging Face Space sleeps after 48h of no traffic, so the first visit
after a quiet stretch waits ~30–60s while the container and the ONNX model load. Acceptable for a
low-traffic tool; worth a friendly "waking up…" state rather than a dead-looking spinner. A keep-warm
ping is possible but adds moving parts — skip it until traffic justifies it.

---

## Phase 2 — Frontend: two screens

The current app has eight routes, a sidebar, and a bottom nav. The product has two screens.

### `/` — the door

One input. One button. The hero already exists and mostly works; the surrounding scaffolding
(`MVP Status` panel, the three feature cards, the stale "AI profile and rec engines are next" copy
that is now actively false) goes.

### `/u/{username}` — the product

Everything on one page:

- **Taste DNA card.** The prose summary first, big, in the serif. Then the tone radar, the genre
  breakdown, the crew affinities, the pretension score. `TasteDNACard`, `ToneRadarChart`,
  `GenreBreakdown`, `CrewAffinities`, and `PretensionScore` already exist and are prop-driven —
  they need new data, not new code.
- **Recommendations.** Eight films. The reason is not secondary text under the poster; the reason
  **is** the card. That's the product.
- **Mood filter.** Inline, above the recommendations. Re-runs call 2 with the mood folded in.
- **Share.** The URL is the share button. It already works.

A sync-in-progress state replaces the page while the job runs — the existing `LoadingTypewriter`
and the job-polling logic in `OnboardingClient.tsx` are both reusable.

### State

Delete `userStore.ts` and the localStorage persistence entirely. The username is in the URL. The
profile comes from the server. There is nothing to persist client-side, and `clear()` was already
dead code with no UI calling it.

---

## Phase 3 — The redesign

The current look is dark-cinematic: near-black backgrounds, gold `#f3c94f` accent, Playfair Display
over DM Sans, a fixed SVG film-grain overlay at 3% opacity, frosted-glass panels. It isn't bad
taste — it's the default "premium dark SaaS" register, and grain-plus-glass reads more 2021-template
than considered.

I'd rather not redesign it inside this document. The right move is to pick a direction together
once the two screens exist and there's real content to design *around* — a real taste summary, real
posters, real reasons. Designing the container before the contents is how you end up with the
current UI.

The one structural note worth making now: this app has exactly one hero object, the Taste DNA card,
and one repeated object, the recommendation. Everything else is chrome. The design should spend all
its budget on those two and be almost aggressively plain everywhere else.

---

## Risks, honestly

**Scraping only works locally — resolved, but know why.** Letterboxd is behind Cloudflare, which
403s datacenter IPs (verified 2026-07-11 on the films page *and* the RSS feed). This killed the
"scrape from the server" idea outright. The resolution is the whole reason ingestion is upload-first:
the public path never scrapes, so there's nothing for Cloudflare to block. `letterboxd.py` survives
as a local-dev convenience and the engine for a possible future hybrid worker or granted API access.

**Export access — resolved.** Confirmed free, no Pro, on 2026-07-11, so the "upload your export"
onboarding is frictionless for everyone. Noted here only because it was once the plan's single
biggest open risk and is now closed.

**Groq's daily cap is the new ceiling.** 1,000 requests/day ÷ 9 per profile ≈ 110 profiles/day. Not
a cost, a *throughput* limit — but it fails differently: at capacity the product must degrade
gracefully ("back tomorrow"), never error. If real demand exceeds it, the levers are batching, a
smaller Groq model for reasons (`llama-3.1-8b-instant` has a 14,400/day cap), or paying. All are
day-there-are-users decisions.

**The public URL exposes an inference, not just data.** The watch history is already public on
Letterboxd, so nothing there is secret. But "you are drawn to films about people failing quietly" is
a claim *about a person*, generated by us, sitting at a guessable URL. The original
`PRODUCT_DECISIONS.md` promised private-by-default and no public profiles; the shareable-URL model
contradicts that. Defensible — but a real decision, made on purpose, not inherited. `noindex` at
minimum.

**Prose quality rides on the ranker, not the model.** With a 70B in production the flat-prose worry
is much reduced, but the principle stands: because the ranker hands over concrete facts, the model
paraphrases rather than invents. If a reason ever reads generic, the *evidence* was thin — fix the
ranker, not the prompt.

**Cold starts on Hugging Face.** The Space sleeps after 48h idle; first visit after a gap waits
~30–60s. A UX papercut, not a correctness bug — cover it with a "waking up" state.

**TMDB enrichment is slow.** Up to three API calls per film (search, details, credits) — ~900 for a
300-film library, and the upload path does the *same* enrichment because the CSV carries no TMDB IDs.
The `letterboxd_tmdb_cache` table already exists and amortizes this across users. The job is async
with progress reporting, so it's a latency problem, not a correctness one.

---

## Order of work

0. ~~Apply for the API beta / verify export access.~~ **Both resolved 2026-07-11:** export is free
   (frictionless upload for everyone), and the API beta is closed (CSV is the permanent public path).
1. ~~**Phase 0** — delete the fiction, drop the DB.~~ **Done 2026-07-10.** 19 files removed, 3 dead
   tables dropped, 4 dead npm deps removed, README rewritten. Backend imports; frontend typechecks.
2. **`ingest.py` + `evidence.py` first, not identity.** Out of order on purpose. Get one real watch
   history in — parse your own Letterboxd export CSV (or scrape locally), enrich via TMDB — then run
   the statistics against it and look at the actual numbers. If contrarianism and patience don't say
   anything interesting about a real viewer, nothing downstream will either. Learn that before
   building two more layers on top. (Parsing the CSV also settles the export-format questions for
   real, with a file in hand.)
3. **`ranker.py`** — `fastembed`, build the taste vector, score, and *measure* with the held-out
   ranking test. This is the product. If it doesn't beat random, stop and fix it.
4. **`writer.py`** — Ollama locally first (free iteration on the two prompts), then the `GroqWriter`
   adapter once the prose is shaped. Same protocol, one env var apart.
5. **Identity + endpoint surface** — `/api/profiles/upload`, username keying, the min-profile gate.
   Cheap, mechanical, waits until there's something worth serving.
6. **Capacity — queue, rate limits, Groq daily-budget cap.** Before anything is publicly reachable.
7. **Phase 2** — collapse the frontend to two screens (upload + `/u/{username}`) against the new API.
8. **Phase 3** — design pass, with real content on screen.
9. **Deploy** — Vercel + Hugging Face Space + Turso, `GroqWriter` on.
10. **v1.1** — accounts (persistence only; magic-link or OAuth, no passwords), plus anti-recs and the
    wild card. All strictly additive on top of the anonymous core — nothing built in v1 gets redone.
