# Cinerex — Deploy (Phase 8)

Everything is free, always-on, no GPU, no residential IP. The build artifacts are ready
(`backend/Dockerfile`, the Turso-aware DB session, the agnostic ORM); what's left needs **your
accounts**, because I can't create accounts or hold your secrets. Follow this in order.

Stack: **Vercel** (frontend) · **Hugging Face Space** (backend, Docker) · **Turso** (libSQL DB) ·
**Groq** (prose). Secrets live only in each platform's secret store — never in the repo.

---

## 1. Groq API key (free, no card)

1. Sign in at **console.groq.com** → API Keys → create a key (`gsk_...`).
2. You'll paste it into the Space secrets (step 3) as `GROQ_API_KEY`.
   (Also add it to your local `D:\CineAI\.env` so I can run the one live `GroqWriter` check that
   closes Phase 4's DoD.)

## 2. Turso database (free)

1. Install the CLI and sign up: `turso auth signup`.
2. Create a DB and a token:
   ```
   turso db create cinerex
   turso db show cinerex --url          # → libsql://cinerex-<org>.turso.io
   turso db tokens create cinerex       # → a long token
   ```
3. Build the `DATABASE_URL` for SQLAlchemy (note the `sqlite+libsql://` scheme and `https`-less host):
   ```
   sqlite+libsql://cinerex-<org>.turso.io/?authToken=<token>&secure=true
   ```
   Tables self-create on first boot (`create_all`) — no migrations.

## 3. Backend → Hugging Face Space (Docker)

1. Create a **new Space** → SDK: **Docker** → **Blank**. No card, no GPU needed.
2. Push the **contents of `backend/`** to the Space repo (the `Dockerfile` must be at the Space
   root). Add this metadata block to the Space's `README.md` so it serves on the right port:
   ```yaml
   ---
   title: Cinerex API
   sdk: docker
   app_port: 7860
   ---
   ```
3. In the Space **Settings → Variables and secrets**, set:
   | Secret | Value |
   |---|---|
   | `GROQ_API_KEY` | your `gsk_...` key |
   | `WRITER_BACKEND` | `groq` |
   | `DATABASE_URL` | the Turso `sqlite+libsql://...` URL from step 2 |
   | `ALLOW_SCRAPE_SYNC` | `false` (Cloudflare 403s the Space; upload is the only public path) |
   | `CORS_ORIGINS` | your Vercel URL, e.g. `https://cinerex.vercel.app` |
4. The Space builds the image (installs `sqlalchemy-libsql` on Linux, bakes in the embedding model).
   First build takes a few minutes. Verify: `GET https://<your-space>.hf.space/health` → `{"status":"ok",...}`.

## 4. Frontend → Vercel

1. Import the repo, set **Root Directory** to `frontend/`.
2. Environment variable: `NEXT_PUBLIC_API_URL = https://<your-space>.hf.space`.
3. Deploy. Then go back to the Space and make sure `CORS_ORIGINS` matches the final Vercel URL
   (including any custom domain).

## 5. Cold start

The Space sleeps after ~48h idle; the first visit then waits ~30–60s while the container and ONNX
model load. The frontend already shows a "Waking the server up…" state for this — no action needed.
A keep-warm ping is possible later but adds moving parts; skip until traffic justifies it.

## 6. Smoke test (do this on the live URLs)

1. Open the Vercel URL in a clean browser.
2. Upload a real Letterboxd export ZIP (Settings → Import & Export → Export Your Data).
3. Watch the profile build, the Taste DNA card appear, and eight reasoned recommendations stream in.
4. Change the mood, re-roll, copy the share URL, open it in a new tab → same profile.
5. Confirm no account was needed, no paid call was made, and nothing was scraped.

At the daily Groq ceiling (~110 profiles) the app shows an honest "at capacity" state, never a 500.

---

## Env var reference

| Variable | Local dev | Production |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./cinerex.db` | Turso `sqlite+libsql://...` |
| `WRITER_BACKEND` | `ollama` | `groq` |
| `GROQ_API_KEY` | (unset) | `gsk_...` (Space secret) |
| `OLLAMA_HOST` | `http://localhost:11434` | (unused) |
| `ALLOW_SCRAPE_SYNC` | `true` | `false` |
| `CORS_ORIGINS` | `http://localhost:3000,...` | your Vercel origin |
| `TMDB_API_KEY` / `TMDB_BEARER_TOKEN` | in root `.env` | Space secrets |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | your Space URL |

Tag the release `v1.0` once the live smoke test passes.
