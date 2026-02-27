# CinematicAI — Master Build Prompt
### A Personalized Movie & TV Recommendation Engine

---

## Overview

Build a smart, AI-powered movie and TV show recommendation platform that ingests a user's real watch history and ratings from Letterboxd and Serializd, deeply analyzes their taste, and delivers hyper-personalized recommendations with human-readable reasoning. The system goes beyond collaborative filtering — it builds a psychological taste profile of the user and recommends based on *who they are as a viewer*, not just *what they've watched*.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | Python + Playwright (handles JS-rendered pages) |
| Movie/Show Metadata | TMDB API (primary), OMDB API (supplementary) |
| Watch History (optional OAuth) | Trakt.tv API |
| AI / LLM | Claude API or OpenAI GPT-4o (for taste profiling + recommendations) |
| Embeddings | OpenAI text-embedding-3-small or equivalent |
| Backend | FastAPI (Python) |
| Frontend | Next.js + Tailwind CSS |
| Database | Supabase (Postgres + vector extension for embeddings) |
| Auth | Supabase Auth |
| Deployment | Vercel (frontend) + Railway or Render (backend) |

---

## Data Ingestion Layer

### Letterboxd
- Letterboxd has no public API. Use web scraping via Playwright.
- Scrape the following from a user's public profile:
  - All films watched (title, year, user rating, date watched)
  - Written reviews (text, star rating, date)
  - Watchlist (films saved but not yet watched)
  - Lists (custom user-created lists)
  - Diary entries (including rewatch flags)
- Also use Letterboxd's public RSS feeds where available as a lighter alternative for recent activity.

### Serializd
- No public API. Use Playwright scraping.
- Scrape:
  - All shows watched (title, seasons watched, user rating)
  - Reviews and notes
  - Watchlist

### TMDB API
- Use TMDB as the primary metadata source after ingestion.
- Match scraped titles to TMDB IDs for reliable data.
- Pull for each film/show: genres, runtime, release year, country, language, director, cast, crew (especially cinematographer, composer, editor), keywords/themes, average rating, popularity score, streaming availability (via TMDB watch providers endpoint), production companies, similar titles, and collection info.

### Trakt.tv (Optional)
- Offer OAuth integration with Trakt for users who prefer it over scraping.
- Use Trakt API to pull watch history, ratings, and watchlist as an alternative ingestion path.

### Data Storage
- Store all ingested data per user in Supabase.
- Maintain a `watched_ids` set per user (TMDB IDs) to filter recommendations.
- Cache TMDB metadata locally to avoid repeat API calls.
- Store raw reviews and rating history for AI analysis.

---

## Taste Profiling Engine (Core AI Layer)

This is the most critical part of the system. After ingestion, run an AI analysis pass to build a structured taste profile for the user. This runs once on first load and updates incrementally as the user logs new watches.

### What to Extract and Store

Send the user's full rating history, review text, and watch patterns to the LLM with a structured prompt. Extract and store:

**Explicit Preferences**
- Top genres (with weighted scores based on average rating within genre)
- Preferred eras/decades (which decades they rate highest on average)
- Preferred languages and countries of origin
- Preferred runtime range

**Deep Taste Signals**
- Pacing preference: fast-paced vs. slow-burn (inferred from genre + review language)
- Tone preference: dark/heavy, light/comedic, melancholic, tense, warm
- Narrative preference: plot-driven, character-driven, atmosphere-driven, idea-driven
- Endings preference: resolution vs. ambiguity (extracted from review text patterns)
- Visual style sensitivity: does the user mention cinematography, aesthetics, or visuals in reviews?
- Dialogue sensitivity: does the user mention writing, scripts, or dialogue?
- Emotional aftertaste: which emotional states (dread, warmth, melancholy, awe, inspiration) correlate with their highest-rated films

**Crew Affinities**
- Directors with above-average ratings from the user
- Cinematographers associated with highly-rated films
- Composers associated with highly-rated films
- Writers/screenwriters associated with highly-rated films
- Actors who appear frequently in top-rated films

**Behavioral Patterns (Invisible Preferences)**
- Correlation between runtime and rating (does longer = higher for this user?)
- Correlation between popularity and rating (do they like obscure or mainstream?)
- Correlation between critical consensus (Metacritic/RT score via OMDB) and their rating — are they a contrarian or a consensus follower?
- Rewatch behavior: which films have they rewatched and what do those have in common?
- Recency patterns: has their taste shifted in the last 12 months vs. historically?

**Negative Signals**
- Genres with below-average ratings
- Tone/styles that correlate with low ratings
- Common traits of their lowest-rated films

Store the taste profile as a structured JSON object in the database. Also store a prose `taste_summary` string generated by the LLM — a single human-readable paragraph describing the user as a viewer.

---

## Recommendation Engine

### Core Recommendation Flow

1. Load user's taste profile from DB
2. Load their `watched_ids` set
3. Query TMDB discover endpoint with filters based on taste profile (genres, language, era, min vote count)
4. Retrieve candidate films/shows (50–100 candidates)
5. Filter out anything in `watched_ids`
6. Score each candidate against the taste profile using embedding similarity + rule-based matching
7. Send top 15–20 candidates + user taste profile to LLM
8. LLM returns ranked final recommendations with a personalized "why you'll like this" explanation for each
9. Return top 5–10 to the user

### Explanation Format (per recommendation)
Each recommendation must include:
- Title, year, poster (from TMDB)
- Streaming availability in user's region
- A 2–3 sentence personalized reason ("why this for you specifically") written in second person, referencing specific things from their profile — not generic
- A match confidence indicator (high / medium / wild card)
- Tags: e.g. [slow burn] [morally complex] [exceptional cinematography]

---

## Features

### 1. Standard Recommendations
The default view. Top 5–10 personalized picks across films and/or TV shows. Filterable by mood, runtime, streaming platform, and format (film vs. show).

---

### 2. Taste DNA Card
A visual, shareable profile card generated for each user showing:
- Their `taste_summary` paragraph (AI-generated prose personality description as a viewer)
- Top 5 genres with percentage weighting
- Favorite era
- Tone profile (a radar/spider chart: dark ↔ light, slow ↔ fast, emotional ↔ intellectual, mainstream ↔ arthouse)
- Crew affinities (top directors, cinematographers)
- Pretension score: where they fall on the scale of crowd-pleaser ↔ contrarian ↔ critical darling chaser ↔ independent
- Shareable as an image card (like a Spotify Wrapped card)

---

### 3. Mood-Based Recommendation
User selects or types their current mood/context. Examples:
- Predefined moods: Comfort watch, Need to cry, Want to be disturbed, Celebrate, Decompress, Can't focus, Date night, Group watch
- Free text: "I had a terrible week and want something that respects my intelligence but doesn't require effort"

The system combines the mood input with the user's taste profile to surface the most fitting option for that specific moment.

---

### 4. The Blind Spot Feature
Analyzes the user's watch history and surfaces:
- Decades they've barely explored (e.g., "You've seen almost nothing from the 1970s")
- Countries/languages they've ignored relative to available acclaimed content
- Genres or subgenres they've avoided
- For each blind spot, recommend the single best entry point — the most accessible, highly-rated film from that area that still aligns with their general taste

Present as a "Your Cinematic Blind Spots" section with gentle framing.

---

### 5. Director / Crew Rabbit Holes
When the user has rated a director's work highly, surface a "Go Deeper" option:
- Full filmography of that director sorted by recommended watch order (not chronological — optimized for taste)
- Highlight which they've seen vs. not seen
- Extend to cinematographers, composers, editors — not just directors
- "You love Denis Villeneuve's films. Here's the ideal order to complete his filmography."

---

### 6. Compatibility Mode (Dinner Party Picker)
User inputs 2–6 Letterboxd or Serializd profile URLs.
- System scrapes and builds taste profiles for each person
- Finds the overlap zone across all profiles
- Recommends 3–5 films/shows that everyone has the highest probability of enjoying
- Shows a compatibility breakdown: where tastes align and where they diverge
- Also surfaces one "compromise pick" that's not everyone's ideal but nobody will hate

---

### 7. Taste Clash
Opposite of compatibility. Input two profiles and the system:
- Shows where the two tastes most violently conflict
- Recommends a "bridge film" — something that could appeal to both based on shared underlying values even if surface preferences differ
- Useful for couples, roommates, film clubs

---

### 8. Hidden Gems Mode
Toggle that filters recommendations to only films/shows with:
- Under a configurable popularity threshold on TMDB (e.g., under 100k votes)
- Still highly rated within that niche
- The goal: zero mainstream picks. No Inception, no Parasite (unless the user hasn't seen them). Surface the overlooked stuff that fits their taste.

---

### 9. Anti-Recommendation
Based on the user's taste profile and negative signals, the system confidently recommends what *not* to watch — specifically popular or critically acclaimed films that, based on the user's pattern, they will probably dislike.
- "Despite the hype, you'll likely find [Film X] frustrating. Here's why, based on your history."
- Framed honestly, not dismissively.
- Include 3–5 anti-recs per session.

---

### 10. Controversial / Wild Card Pick
Alongside safe recommendations, always surface one film that:
- Goes against the user's obvious taste patterns
- Has a notable chance of surprising them based on secondary signals in their profile
- Clearly labeled as a wild card with explanation: "This isn't your usual thing, but here's why it might click."

---

### 11. Watchlist Ranker
If the user has an existing Letterboxd watchlist:
- Import it
- Rank the watchlist by what they should watch first, based on current mood + taste profile + streaming availability
- "Out of your 47 saved films, here are the 5 you should actually watch this weekend."

---

### 12. The Rewatch Predictor
Analyzes the user's historical ratings and taste evolution.
- Identifies films they rated lower in the past that, based on how their taste has matured, they'd likely appreciate more today.
- "You gave this 3 stars in 2020, but based on what you've loved since then, you might rate it 4.5 today."
- Surface as a "Second Look" section.

---

### 13. Film Twin Finder
Matches the user with another user on the platform (opt-in) whose taste profile is most similar — not a friend, a stranger with an eerily similar viewing fingerprint.
- Show the overlap stats
- Surface films the twin has rated highly that the user hasn't seen yet
- "Your film twin has seen 12 films you haven't — here are their top picks you'd probably love."

---

### 14. Thematic Universe Builder
Groups films not by genre but by underlying theme.
- AI clusters the user's highest-rated films into thematic threads: e.g., "films about the cost of ambition," "films where grief is treated as transformation," "films about lonely people finding unexpected connection"
- For each cluster, recommend 3–5 unwatched films that belong to the same thematic space
- This is the most differentiated recommendation surface — purely semantic, not genre-based

---

### 15. Cinematic Context Cards
For recommended foreign-language films or older films the user might not have cultural context for:
- Attach a small card with spoiler-free background: historical context, why it matters in cinema history, what to watch for
- Makes users better viewers and reduces the intimidation of unfamiliar films

---

### 16. Streaming-Aware Filtering
- All recommendations include current streaming availability in the user's detected region (via TMDB watch providers)
- User can filter: "Only show me things on services I have"
- User inputs which services they subscribe to; this is saved to their profile
- Availability is checked at recommendation time (not cached too long — stream availability changes)

---

### 17. Runtime Matcher
User inputs available time: "I have 90 minutes."
- System finds the best-matching film within ±10 minutes of that runtime
- Combined with taste profile — not just any 90-minute film, the *best* 90-minute film for them right now

---

### 18. Prediction Game
Before the user watches a recommended film, the AI predicts their star rating.
- After they log the watch on Letterboxd, they can return and see how accurate the prediction was.
- Track prediction accuracy over time per user.
- Show a running accuracy score: "CinematicAI has predicted your rating within 0.5 stars 73% of the time."
- Gamification hook — users will want to come back and report their actual rating.

---

### 19. Taste Challenge (Weekly)
Every week, serve the user a small cinematic challenge:
- "Watch one film from a country you've never watched before"
- "Try a film from the 1960s this week — here's the best entry point for your taste"
- "Watch something with a runtime over 3 hours — we think you're ready for this one"
- Track completion. Optional streak counter.

---

### 20. Taste Drift Alerts
Monitor the user's recent watch/rating history (last 30–90 days) vs. their historical baseline.
- If patterns shift — e.g., suddenly rating comedies higher, or watching more TV than films — surface a gentle alert.
- "Your taste seems to be shifting lately. Want more recommendations in that direction?"
- User can confirm or dismiss. Confirmed shifts update the taste profile weighting.

---

### 21. The Debate Pick
For users who want a film specifically to spark conversation:
- Recommends films with divisive interpretations, open endings, or moral ambiguity
- Filtered to match the user's taste threshold — not random provocations, but films they'll actually care about and have opinions on
- Ideal for film clubs, dates, friend groups

---

### 22. Post-Watch Reflection Prompt
When a user logs a new watch (or syncs from Letterboxd), trigger a soft prompt:
- Two quick optional questions: "What stayed with you?" and "What would you have changed?"
- Freeform text responses stored and fed back into the AI taste profiling layer
- Makes the data richer over time and makes logging feel more meaningful than just star ratings

---

### 23. Seasonal / Contextual Awareness
- Detect approximate time of year and subtly factor ambient context into recommendations
- Not "Christmas movies" — more nuanced: e.g., in winter, lean toward atmospheric, slow-burn, interior films; in summer, more kinetic or adventurous picks
- This should be a soft signal, not a dominant filter

---

### 24. Taste Evolution Timeline
A visual timeline showing how the user's taste has shifted year by year:
- Average rating per year, top genre per year, average film era watched per year
- Narrative summary: "In 2021 you were deep into arthouse European cinema. In 2023 you shifted toward American genre films."
- Scrollable, visually engaging — a history of the user as a viewer

---

## User Onboarding Flow

1. User lands on the home page
2. Input Letterboxd username (required) and/or Serializd username (optional)
3. System scrapes profiles — show a progress indicator ("Building your taste profile...")
4. Run TMDB enrichment and AI taste analysis in the background
5. First reveal: show the user their Taste DNA card before any recommendations
6. Let the user confirm, adjust, or add context ("Anything we got wrong?")
7. Deliver first batch of recommendations
8. Ask which streaming services they have
9. Optional: connect Trakt.tv for ongoing sync

---

## AI Prompting Strategy

### Taste Profile Generation Prompt (run once per user)

```
You are a film taste analyst. Given the following watch history, ratings, and reviews from a Letterboxd user, build a detailed taste profile.

Data:
[INJECT: structured list of films with ratings, genres, directors, and review excerpts]

Return a JSON object with the following fields:
- top_genres: array of {genre, avg_rating, count}
- preferred_eras: array of {decade, avg_rating}
- tone_profile: {dark_light: float, slow_fast: float, emotional_intellectual: float, arthouse_mainstream: float} (all -1 to 1 scale)
- narrative_preference: "plot" | "character" | "atmosphere" | "ideas"
- pacing_preference: "slow_burn" | "moderate" | "fast_paced"
- crew_affinities: {directors: [], cinematographers: [], composers: []}
- invisible_preferences: array of strings (non-obvious patterns detected)
- negative_signals: array of strings (what to avoid)
- emotional_aftertastes: array of {emotion, correlation_score}
- taste_summary: string (1 paragraph, second person, describing this viewer's cinematic identity)
- pretension_score: float (-1 = pure crowd pleaser, 1 = extreme contrarian)
```

### Recommendation Generation Prompt

```
You are a personalized film recommender. Given the user's taste profile and a list of candidate films, select and rank the best recommendations. For each, write a 2-3 sentence explanation in second person that references specific elements of their taste profile. Be specific — never use generic phrases like "fans of this genre will enjoy." Reference their actual preferences.

User taste profile:
[INJECT: taste profile JSON]

Candidate films:
[INJECT: list of candidates with TMDB metadata]

Already watched (exclude these):
[INJECT: watched_ids]

Return: ranked array of {tmdb_id, title, reason, tags, confidence: "high"|"medium"|"wild_card"}
```

---

## Phased Build Plan

### Phase 1 — MVP
- Letterboxd scraper (films + ratings)
- TMDB metadata enrichment
- Basic AI taste profiling
- Standard recommendations with "why you'll like this" explanations
- Taste DNA card (text only)
- Streaming availability filter

### Phase 2
- Serializd integration (TV shows)
- Mood-based recommendations
- Hidden gems mode
- Watchlist ranker
- Anti-recommendations
- Blind spot feature
- Runtime matcher

### Phase 3
- Compatibility / Dinner Party Picker
- Film Twin Finder
- Prediction Game
- Thematic Universe Builder
- Taste Evolution Timeline
- Weekly Taste Challenges
- Post-watch reflection prompts
- Cinematic Context Cards
- Taste Drift Alerts

### Phase 4
- Trakt.tv OAuth integration
- Native mobile app
- Film club / social layer
- Shareable Taste DNA image card (Spotify Wrapped style)
- Public taste profiles

---

## Key Design Principles

- **Taste-based, not item-based.** Every recommendation should feel like it came from someone who *knows* the user, not an algorithm that noticed surface-level similarity.
- **Explain everything.** Never surface a recommendation without a personalized reason. The "why" is as important as the "what."
- **Respect intelligence.** Don't simplify. Users who care about their film taste are thoughtful — talk to them that way.
- **No already-watched films.** Ever. This is a hard filter, not a soft one.
- **Freshness.** Recommendations should feel different each session. Don't resurface the same picks.
- **Honesty over flattery.** The anti-recommendation and wild card features exist because honest, occasionally uncomfortable suggestions are more valuable than safe ones.

---

*End of Master Build Prompt*
