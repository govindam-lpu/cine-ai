# Cinerex

Taste-based film recommendations. Upload your Letterboxd export, get a statistical portrait of
yourself as a viewer and eight films with a real, specific reason attached to each. No login. No
paid API. No scraping in production.

**Status:** Rebuilding from a clean slate. The previous working build is preserved under
[`archive/`](archive/); the new build starts fresh and cherry-picks from it.

## Start here

Everything needed to build v1 lives in [`docs/`](docs/), written so a fresh session can execute it
end to end:

| Doc | What it is |
|---|---|
| [`docs/00_MASTER_PROMPT.md`](docs/00_MASTER_PROMPT.md) | Paste into a new session to build the whole thing, phase by phase. |
| [`docs/01_BUILD_PHASES.md`](docs/01_BUILD_PHASES.md) | The nine phases (0–8): scope, edge cases, tests, definition of done. |
| [`docs/02_HANDOVER.md`](docs/02_HANDOVER.md) | State of the world: archive map, secrets, how to run, progress checklist. |
| [`docs/PLAN.md`](docs/PLAN.md) | The rationale — *why* every decision is what it is. Read first. |
| [`docs/DESIGN.md`](docs/DESIGN.md) · [`docs/PRIVACY_LEGAL.md`](docs/PRIVACY_LEGAL.md) | Design reference (Phase 7) and data-handling stance. |

## The shape of it, in one glance

```
Upload Letterboxd export (ZIP/CSV)
      │
      ▼
  parse ──► TMDB enrich ──► evidence (pure-Python stats) ──► ranker (local embeddings)
                                                                   │  top 8 + why-each-scored
                                                                   ▼
                                                          writer (LLM writes prose only)
                                                                   │
                                                                   ▼
                                              Taste DNA card + 8 reasoned recommendations
```

The model never decides — it only writes. Ranking and taste analysis are plain Python and local
embeddings; a free LLM (Groq in prod, Ollama locally) phrases the "why." Free to run, no GPU or
residential IP required.

## Stack

Next.js (Vercel) · FastAPI (Hugging Face Space) · Turso (SQLite-compatible) · fastembed (ONNX, CPU) ·
Groq `llama-3.3-70b-versatile` / local Ollama. All free tiers.

## Run it locally

Backend (FastAPI) and frontend (Next.js 14) live at the repo root. A Python venv is at `.venv`.

```bash
# backend  → http://127.0.0.1:8000  (GET /health)
cd backend && pip install -r requirements.txt
uvicorn main:app --reload
pytest

# frontend → http://localhost:3000
cd frontend && npm install
npm run dev
npm run test        # vitest
npm run typecheck   # tsc --noEmit

# both, containerized
docker compose up
```

Reset the local database: delete the SQLite file (`backend/cinerex.db`) and restart — v1 has no
migrations; tables self-create on startup.

## Archive

[`archive/`](archive/) is the complete prior build, kept for reference — the Letterboxd scraper and
TMDB client (both good, ported forward) and the React components worth reusing. It is reference only;
nothing there is imported by the new build at runtime.
