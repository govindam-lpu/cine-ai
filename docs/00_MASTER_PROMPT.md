# Cinerex — Master Build Prompt

> **Paste this whole file as the first message in a fresh session.** It has no memory of the
> conversation that produced it; everything it needs is here or in the three files it points to.

---

You are building **Cinerex**, a taste-based film recommender, from a clean slate. A previous
planning session decided the architecture, verified the constraints, and archived a working older
version to cherry-pick from. Your job is to build the real thing, phase by phase, to production
quality — no stubs, no placeholder data, no "TODO later" left in committed code.

## Read these first, in order

1. **`docs/PLAN.md`** — the *why*. The full rationale for every decision below. Read it once, fully,
   before writing any code. When a constraint here seems arbitrary, PLAN.md explains it.
2. **`docs/01_BUILD_PHASES.md`** — the *what and how*. Nine phases (0–8), each with scope, tests,
   edge cases, and a definition of done. This is your work queue.
3. **`docs/02_HANDOVER.md`** — the *state of the world*. What's in `archive/`, what secrets exist,
   how to run and test, and a progress checklist you keep updated.

## What Cinerex is

A user uploads their Letterboxd export (a ZIP of CSVs). We compute — in plain Python — a rich
statistical portrait of them as a viewer, rank candidate films against it with local embeddings, and
have a language model write a short, specific, second-person reason for each pick. They get a Taste
DNA card and eight recommendations, each with a real "why this, for you." They can tweak and re-roll.
No login. Optionally, later, an account to save it all.

## Non-negotiable constraints — do not "improve" these away

These are decisions, not defaults. Each was made against a real constraint. If you think one is
wrong, **stop and flag it** — do not silently reverse it.

1. **Ingestion is CSV/ZIP upload, not scraping.** Letterboxd is behind Cloudflare, which 403s
   datacenter IPs (verified). A deployed scraper cannot work. The scraper in `archive/` is ported
   only as a *local-development* convenience; the public path is upload. Never make scraping the
   production ingestion path.
2. **The model never decides anything — it only writes.** Ranking and taste analysis are done in
   Python (statistics + embeddings). The LLM is handed concrete facts and asked to phrase them. Do
   not ask the model to rank films, judge taste, or reason about the user. That path is deliberately
   closed; it is slower, costlier, and worse.
3. **No paid inference.** Prose comes from **Groq** (`llama-3.3-70b-versatile`, free tier) in
   production and **Ollama** (`llama3.2:3b-instruct-q4_K_M`) in local dev, behind one `Writer`
   interface chosen by env var. No OpenAI, no Anthropic billing, in the runtime path.
4. **Anonymous in v1. Accounts are v1.1.** v1 has zero auth — upload, profile, recs, tweaks, all
   session-scoped. Do not build login, sessions, or user accounts in v1. The free/account line, when
   accounts arrive, is drawn at *persistence* (saving), never at *features*.
5. **Embeddings are local and in-memory.** Use `fastembed` (ONNX, no PyTorch) with
   `all-MiniLM-L6-v2`. No pgvector, no vector database — a few thousand vectors live in memory and
   `numpy` does the cosine similarity.
6. **Database is SQLite locally, Turso in production, one connection string apart.** Keep the ORM
   database-agnostic: no SQLite-specific SQL, no raw `PRAGMA`. No Postgres, no Supabase.
7. **Design comes last (Phase 7).** Build the two screens functional and plain first. Do not spend
   effort on visual polish until there is real content to design around.

## How to work

- **One phase at a time, in order.** Do not start Phase N+1 until Phase N meets its Definition of
  Done in `01_BUILD_PHASES.md`, including its tests.
- **Tests are part of every phase, not a final phase.** Backend: `pytest`. Frontend: `vitest` +
  `tsc --noEmit`, and Playwright for the end-to-end journey once the UI exists. A phase with failing
  or absent tests is not done.
- **Commit at each phase boundary** with a clear message (`feat(phase-1): CSV ingestion + TMDB
  enrichment`). This is what makes the build resumable across sessions.
- **Update the progress checklist** in `docs/02_HANDOVER.md` as you complete each phase, so a later
  session (or the user) can see exactly where things stand.
- **Reuse from `archive/`, deliberately.** `02_HANDOVER.md` lists what's worth porting (the scraper,
  the TMDB client, the React components, the design tokens) and what to ignore (the heuristic
  "AI", the dead routers, the Supabase stub). Port by understanding and adapting, not blind copy —
  the models and API surface are changing.
- **No stub data in commits.** Test fixtures live under `tests/` and are clearly fixtures. The app
  itself must never ship hardcoded film lists, fake profiles, or mock responses standing in for real
  logic. If a real implementation isn't ready, the phase isn't done.
- **When you hit a genuine unknown** (a library API you're unsure of, an ambiguous product call),
  check the current official docs first; if it's a product decision, stop and ask. Do not guess and
  move on.

## Verify facts, don't trust memory, for these

Some specifics drift. Confirm against current official docs at build time rather than assuming:
`fastembed`'s exact model identifier and API; the Turso/libSQL SQLAlchemy dialect and connection
string; Groq's structured-output/JSON parameter and current free-tier limits; Ollama's `format`
parameter. The verified-as-of-planning facts (model IDs, the ~1,000 req/day Groq cap, the Cloudflare
403 behavior) are recorded in `PLAN.md` — treat those as starting points, not gospel, and re-check
anything that would break loudly if wrong.

## Definition of done for the whole build

A stranger can open the deployed site, upload their Letterboxd export, watch a real taste profile and
eight genuinely-reasoned recommendations appear, tweak them, and share the URL — with no account, no
paid API call, and no scraping. Every phase's tests pass. Nothing in the committed tree is a stub.

Start by reading `docs/PLAN.md` in full, then `docs/01_BUILD_PHASES.md`, then begin Phase 0.
