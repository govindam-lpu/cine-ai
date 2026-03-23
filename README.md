# Cinerex — Project Folder

This folder contains the complete specification for building Cinerex — an AI-powered, taste-based movie and TV show recommendation engine. Every document in this folder is a source of truth. When building, reference all documents together.

---

## What is Cinerex?

Cinerex ingests a user's public Letterboxd and Serializd profiles, builds a deep psychological taste profile using AI, and delivers hyper-personalized film and TV recommendations with human-readable reasoning. It recommends based on *who the user is as a viewer* — not just what they've watched.

**App Name:** Cinerex
**Status:** Pre-build. All specs complete.
**Monetization:** Free at launch. Freemium model to be introduced later.
**Auth:** Users connect via public Letterboxd/Serializd username only. No credentials stored.
**Social:** Private. No public user profiles on the platform.

---

## Document Index

| File | What It Covers |
|---|---|
| `README.md` | This file. Project overview and folder guide. |
| `MASTER_PROMPT.md` | Full feature list, AI strategy, tech stack, build phases |
| `DESIGN.md` | Visual identity, color system, typography, component specs, page layouts |
| `PROJECT_STRUCTURE.md` | Folder and file architecture for frontend and backend |
| `DATABASE_SCHEMA.md` | All Supabase tables, columns, types, relationships, indexes |
| `API_CONTRACT.md` | Every API endpoint — method, path, request, response, errors |
| `SCRAPER_SPEC.md` | Letterboxd + Serializd scraping rules, fields, fallbacks, sync logic |
| `PRODUCT_DECISIONS.md` | Business rules, edge cases, feature flags, launch constraints |
| `PRIVACY_LEGAL.md` | Data handling, retention policy, ToS notes, scraping stance |

---

## Tech Stack Summary

| Layer | Tool |
|---|---|
| Frontend | Next.js 14 + Tailwind CSS + shadcn/ui |
| Backend | FastAPI (Python 3.11+) |
| Scraping | Playwright + BeautifulSoup4 |
| Movie Metadata | TMDB API + OMDB API |
| AI / LLM | Anthropic Claude API |
| Embeddings | OpenAI text-embedding-3-small |
| Database | Supabase (Postgres + pgvector) |
| Auth | Supabase Auth |
| Deploy | Vercel (frontend) + Railway (backend) |

---

## Build Phases

- **Phase 1 (MVP):** Letterboxd scraper → TMDB enrichment → AI taste profile → recommendations with reasons → Taste DNA card → streaming filter
- **Phase 2:** Serializd (TV), mood recs, hidden gems, watchlist ranker, anti-recs, blind spots
- **Phase 3:** Compatibility mode, film twin, prediction game, thematic universe, taste evolution
- **Phase 4:** Trakt OAuth, mobile app, shareable DNA card, taste challenges

---

## Local Development

- Frontend only from the repo root: `npm run dev`
- Frontend directly: `cd frontend && npm run dev`
- Frontend production build: `npm run build`
- Docker Compose: `docker compose up --build` now starts both backend on port 8000 and frontend on port 3000

> Note: the frontend is now wired to the backend endpoints that exist today (`/health`, `/users`, `/scrape/letterboxd`, `/scrape/status/:job_id`). Recommendation, watchlist, compatibility, and twin pages are fully built in the UI and clearly mark which backend endpoints are still pending.

## How to Use This Folder

Point your AI coding agent (Copilot, Cursor, Claude Code, etc.) at this entire folder or repo. Say:

> "Reference all documents in this folder and build [specific feature/file]. Follow the architecture in PROJECT_STRUCTURE.md, use the schema in DATABASE_SCHEMA.md, implement the endpoints in API_CONTRACT.md, and follow design specs in DESIGN.md."

Every document is written to be agent-readable — precise, structured, unambiguous.
