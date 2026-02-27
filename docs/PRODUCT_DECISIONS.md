# Cinerex — Product Decisions & Business Rules

This document captures all product-level decisions that affect how the system is built. Treat these as binding rules, not suggestions.

---

## Monetization

**Current status:** Free. No payments, no tiers, no feature gates.

**Future freemium model (Phase 4+):**
When introduced, the likely split is:

| Feature | Free | Pro |
|---|---|---|
| Basic recommendations | ✅ | ✅ |
| Taste DNA card | ✅ | ✅ |
| Mood-based recs | ✅ | ✅ |
| Watchlist ranker | Limited (10 items) | Unlimited |
| Compatibility mode | 2 profiles | Up to 6 |
| Film Twin | ✅ | ✅ |
| Blind Spots | ✅ | ✅ |
| Thematic Universe | ❌ | ✅ |
| Prediction Game | 5/month | Unlimited |
| Taste Evolution Timeline | ❌ | ✅ |
| Weekly Challenges | ❌ | ✅ |
| Auto-sync | Manual only | Weekly auto |
| Shareable DNA card (PNG export) | ❌ | ✅ |

**Do not build paywalls yet.** Build all features as if they're free. Add gates later when monetization is introduced.

---

## Authentication

- Users are identified by their Letterboxd username at first entry
- Supabase Auth is used for session management
- **No password login at launch.** Use magic link (email) or anonymous session
- Anonymous sessions: Users can get recommendations without an account. Profile is saved to local storage. Prompted to create an account to save permanently.
- Email is optional — collected only if user wants to save their profile

---

## Profile Access & Privacy

- Cinerex only scrapes **public** Letterboxd and Serializd profiles
- If a profile is private: show a clear error message, do not attempt to scrape
- If a profile becomes private **after** scraping: keep existing data, mark profile as `is_private: true`, do not re-scrape until made public again
- Users' data on Cinerex is **private by default** — no public profiles, no leaderboards, no browsable user list
- Film Twin feature is **opt-in** — user must explicitly enable it in settings. Off by default.
- Compatibility mode uses external Letterboxd usernames — those users do NOT get a Cinerex profile created for them

---

## Data Freshness

- Taste profiles are considered **stale after 30 days** or after 20+ new films are logged
- When stale, show a "Profile may be outdated — sync now?" nudge (not an auto-sync)
- TMDB metadata is considered **fresh for 90 days** — refresh after that on next access
- Streaming availability is considered **fresh for 7 days** — refresh weekly
- Recommendations are **never cached** — generated fresh per session

---

## Minimum Viable Profile

A taste profile cannot be generated until:
- At least **25 films** are in watch history
- At least **15 of those films have a user rating** (not just logged without stars)

Below this threshold:
- Show a friendly message: *"Log a few more films on Letterboxd and come back — we need at least 25 to understand your taste."*
- Do not generate a partial or low-quality profile

---

## Recommendation Rules (Non-Negotiable)

1. **Never recommend a film the user has already watched.** This is a hard filter, not a soft one. Check against `watched_ids` before any film is surfaced.
2. **Never recommend the same film twice in one session.**
3. **Never show a film without a "why" explanation.** Every recommendation must include a personalized reason string.
4. **Anti-recommendations must be framed honestly, not cruelly.** "You'll likely find this frustrating because..." not "This is bad."
5. **Wild card picks must be clearly labeled.** Never sneak a wild card in as a regular recommendation.
6. **Streaming unavailability must be shown, not hidden.** If a film isn't on any of the user's services, show it but label it clearly — don't hide good recommendations.

---

## AI Usage Rules

- All LLM calls use **Claude API (Anthropic)** as primary
- Embeddings use **OpenAI text-embedding-3-small** — separate from generation
- All LLM responses must be parsed and validated before being stored or returned to the frontend
- If an LLM response fails to parse as valid JSON, retry once. If it fails again, fall back to a rule-based recommendation (no explanation text)
- Never expose raw LLM output to the user — always parse into structured data first
- LLM calls for taste profiling run **server-side only** — never from the frontend
- Log all LLM token usage per user per day for future cost monitoring

---

## Scraping Ethics & Legal Stance

- Cinerex only scrapes publicly accessible profile pages — no login, no credentials
- Scraping is done with respectful rate limiting (delays between requests)
- User data scraped from Letterboxd is only used to serve that user's own recommendations — it is not shared, sold, or used to train models
- If Letterboxd or Serializd sends a cease-and-desist or officially blocks scraping, stop immediately and remove that integration
- Cinerex is not affiliated with Letterboxd or Serializd
- Cinerex does not cache or republish Letterboxd/Serializd content — only processes it for the user's own benefit

---

## Content Policy

- Cinerex surfaces films and shows from TMDB's catalog
- Do not filter out adult content in the recommendation engine — TMDB has `adult: false` flag and only standard content is included by default
- No manual curation of the film catalog — rely entirely on TMDB data
- If a TMDB film has a `vote_count` under 10, exclude it from recommendations (too low signal)

---

## Feature Flags (Phase 1 Launch)

Features enabled at launch:
- [x] Letterboxd scraping
- [x] TMDB enrichment
- [x] AI taste profiling
- [x] Standard recommendations
- [x] Mood-based recommendations
- [x] Taste DNA card (text view)
- [x] Streaming filter
- [x] Anti-recommendations
- [x] Hidden gems mode

Features disabled at launch (Phase 2+):
- [ ] Serializd integration
- [ ] Watchlist ranker
- [ ] Compatibility mode
- [ ] Film Twin
- [ ] Blind Spots
- [ ] Prediction Game
- [ ] Thematic Universe Builder
- [ ] Taste Evolution Timeline
- [ ] Weekly Challenges
- [ ] Shareable DNA card (PNG export)
- [ ] Post-watch reflections

---

## Error Messaging Principles

- Never show raw error messages or stack traces to users
- Every error state has a friendly, specific message in the Cinerex voice
- Error messages suggest a concrete next step where possible
- Loading states always show progress — never just a spinner with no context

Example messages:
| Situation | Message |
|---|---|
| Profile is private | *"Your Letterboxd profile is set to private. Make it public and we can get started."* |
| Not enough films | *"You've logged {n} films so far. We need at least 25 to understand your taste properly. Watch a few more and come back."* |
| Scrape failed | *"We couldn't reach Letterboxd right now. Try again in a few minutes."* |
| AI generation failed | *"Something went wrong building your profile. Your data is safe — hit retry and we'll try again."* |
| No streaming match | *"Not on your streaming services right now, but worth finding."* |

---

## Performance Expectations

| Operation | Target Response Time |
|---|---|
| Profile page load (cached data) | < 800ms |
| Recommendation generation | < 4s |
| Full Letterboxd scrape (300 films) | < 90s (async, user sees progress) |
| Taste profile generation (AI) | < 20s |
| Compatibility analysis | < 8s |
| Watchlist ranking | < 3s |

---

## Analytics (Phase 2+)

At launch: no analytics. In Phase 2, add anonymous usage tracking (Plausible or PostHog) with:
- Page views
- Features used
- Scrape success/failure rates
- Recommendation refresh rate (are users getting value?)

No personally identifiable analytics. No selling data. No third-party ad pixels.
