# Cinerex — Scraper Specification

This document defines exactly what to scrape from Letterboxd and Serializd, how to handle edge cases, and how the sync cycle works. The scraper is the most fragile part of the system — treat it accordingly.

---

## General Rules

1. **Never store usernames or passwords.** Cinerex only accesses public profiles. No login required.
2. **All scraping runs server-side** in the FastAPI backend. Never in the browser.
3. **Use Playwright** for JavaScript-rendered pages. Use `httpx` + `BeautifulSoup` for static pages where sufficient.
4. **Respect rate limits.** Add random delays between requests. Never hammer a domain.
5. **Cache aggressively.** TMDB metadata once fetched is stored locally — never re-fetch the same film ID.
6. **Handle failures gracefully.** A single failed page should not abort an entire scrape job. Log and continue.
7. **Scraper code must be isolated** in `/backend/app/scrapers/` — business logic lives in `/backend/app/services/`.

---

## Letterboxd Scraper

### Entry Point
```
https://letterboxd.com/{username}/
```

### Pre-flight Check
Before scraping, fetch the profile page and verify:
- Profile exists (no 404)
- Profile is not locked/private (check for "This member has made their account private" message)
- Store `display_name`, `avatar_url`, and `bio` from the profile page

### Pages to Scrape

#### 1. Films — All Watched (`/films/`)
URL pattern: `https://letterboxd.com/{username}/films/page/{n}/`
Iterate pages until empty.

Fields per film entry:
```
film_name       — text content of the film title element
film_year       — year in parentheses next to title
letterboxd_slug — from href, e.g. /film/the-godfather/
user_rating     — number of filled stars (0.5 increment), null if no rating
date_watched    — from diary if available, else null
is_rewatch      — boolean, presence of rewatch indicator
liked           — boolean, presence of heart icon
```

Pagination: Each page contains 72 entries. Stop when a page returns 0 entries.

#### 2. Diary (`/films/diary/`)
URL: `https://letterboxd.com/{username}/films/diary/`
Scrape all diary entries to get precise watch dates (not just "watched" status).

Fields per diary entry:
```
film_name       — title
letterboxd_slug — /film/slug/
watched_date    — exact date (YYYY-MM-DD)
user_rating     — 0.5–5.0, null if not rated
is_rewatch      — boolean
```

#### 3. Reviews (`/films/reviews/`)
URL: `https://letterboxd.com/{username}/films/reviews/`

Fields per review:
```
film_name       — title
letterboxd_slug — /film/slug/
review_text     — full review body (strip HTML tags, keep plain text)
user_rating     — rating at time of review
review_date     — date of review
contains_spoilers — boolean
```

Do not scrape reviews with spoiler warnings — flag `review_text` as null and `contains_spoilers` as true.

#### 4. Watchlist (`/watchlist/`)
URL: `https://letterboxd.com/{username}/watchlist/`
Same pagination as /films/.

Fields per entry:
```
film_name       — title
letterboxd_slug — /film/slug/
added_date      — if available
```

#### 5. Lists (`/lists/`)
Scrape list names and the films in each list. Used to detect thematic preferences.

Fields per list:
```
list_name       — title of the list
list_description — optional description
film_slugs      — array of film slugs in the list
```

---

### Letterboxd → TMDB Matching

After scraping, each `letterboxd_slug` must be resolved to a TMDB ID.

Process:
1. Extract film name and year from the slug/page
2. Search TMDB: `GET /search/movie?query={name}&year={year}`
3. Take the top result if confidence is high (title similarity > 0.9 AND year matches)
4. If no confident match: try without year, then take the best match
5. If still no match: log as unmatched, skip (do not create a `films` row)
6. Store the mapping: `letterboxd_slug → tmdb_id` in a local cache table

Do not call TMDB if the slug is already cached.

---

### Rate Limiting — Letterboxd

- Add `1.5s – 3.5s` random delay between page requests
- If a 429 or Cloudflare challenge page is detected, back off for `60s` and retry up to 3 times
- If still blocked after 3 retries, mark the sync job as `error` with code `SCRAPE_BLOCKED`
- Set a realistic User-Agent string (recent Chrome browser)
- Run a maximum of 1 concurrent Letterboxd scrape at any given time across the whole system

---

## Serializd Scraper

### Entry Point
```
https://serializd.com/user/{username}
```

### Pre-flight Check
Same as Letterboxd — verify profile exists and is public.

### Pages to Scrape

#### 1. Watched Shows
URL: `https://serializd.com/user/{username}/watched`

Fields per show:
```
show_name       — title
serializd_slug  — from href
user_rating     — 0–10 scale (normalize to 0.5–5.0 by dividing by 2)
seasons_watched — array of season numbers, or "all"
```

#### 2. Reviews
URL: `https://serializd.com/user/{username}/reviews`

Fields per review:
```
show_name       — title
review_text     — plain text
user_rating     — normalized
review_date     — date
season_specific — season number if review is season-specific, else null
```

#### 3. Watchlist
URL: `https://serializd.com/user/{username}/watchlist`

---

### Serializd → TMDB Matching

Same approach as Letterboxd, but use `GET /search/tv?query={name}` instead of movie search.

---

### Rate Limiting — Serializd

Same rules as Letterboxd. Serializd is a smaller service — be especially conservative.

---

## Sync Modes

### Full Sync
Triggered on:
- First time a user connects their profile
- User manually triggers "re-sync everything"

Behavior:
- Scrape all pages from the beginning
- Match all films to TMDB
- Fetch TMDB metadata for any new films
- Run AI taste profiling from scratch

### Incremental Sync
Triggered on:
- Subsequent syncs (scheduled or user-triggered)

Behavior:
- Only scrape the first 2–3 pages of `/films/` and `/films/diary/` (recent activity)
- Compare against existing `watch_history` rows
- Only insert new entries
- If more than 50 new films found, escalate to full sync automatically
- Run AI taste profile *update* (not full regeneration) with the new data

### Scheduled Sync
Do not auto-sync in the background at launch (Phase 1). Users trigger syncs manually.
Phase 2: add optional weekly auto-sync, user opt-in only.

---

## Data Normalization Rules

| Raw Value | Normalized Value |
|---|---|
| Letterboxd rating "★★★½" | `3.5` |
| Letterboxd rating "½" | `0.5` |
| No rating given | `null` (not `0`) |
| Serializd rating "7/10" | `3.5` (divide by 2) |
| Date "27 Jan 2024" | `"2024-01-27"` |
| Date not present | `null` |
| Review with only whitespace | `null` |
| Spoiler review | `null` for text, `contains_spoilers: true` |

---

## Failure Handling

| Failure | Behavior |
|---|---|
| Profile goes private mid-scrape | Stop, mark sync error `PROFILE_PRIVATE`, notify user |
| Single film page 404 | Log and skip, continue scraping |
| TMDB returns no match | Log as `unmatched`, skip film, do not crash |
| TMDB API rate limit hit | Wait 10s, retry. Max 3 retries before failing |
| Playwright browser crash | Restart browser, retry current page. Max 2 retries |
| Page structure changed (HTML) | Log a `SCRAPER_STRUCTURE_CHANGED` error for that page, continue with rest |
| Cloudflare block | Back off 60s, retry 3 times, then fail with `SCRAPE_BLOCKED` |
| Timeout > 30s per page | Skip page, log warning |

---

## HTML Structure Reference (as of Jan 2025)

Letterboxd and Serializd can change their HTML at any time. The scraper must be written defensively — never assume a selector will always exist. Always use `try/except` around selector access.

**Letterboxd film grid item (current):**
```css
ul.poster-list > li.poster-container > div[data-film-name][data-film-year][data-film-slug]
```
Rating is in `span.rating`.
Rewatch indicator is `span.rewatch`.

**This is subject to change.** When structure changes, the scraper logs `SCRAPER_STRUCTURE_CHANGED` and the dev team updates selectors. Do not hardcode more than necessary.

---

## What NOT to Scrape

- Any page requiring login
- Other users' activity (only the authenticated user's own profile)
- Film pages on Letterboxd (get metadata from TMDB instead)
- Comments or social activity
- Any personally identifiable information beyond display name and avatar

---

## Scraper Health Monitoring

Log the following metrics per scrape job:
- Start time, end time, duration
- Total pages scraped
- Total films found
- Total TMDB matches (and match rate)
- Total failures/skips
- Final status

Store these in a `scrape_logs` table (optional at MVP, required by Phase 2).
