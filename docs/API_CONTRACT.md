# Cinerex — API Contract

Base URL: `http://localhost:8000` (dev) / `https://api.cinerex.app` (prod)
All responses use the envelope format:
```json
{ "success": true, "data": { ... }, "error": null }
{ "success": false, "data": null, "error": { "code": "ERROR_CODE", "message": "..." } }
```
All timestamps are UTC ISO 8601 strings.
Authentication: Supabase JWT passed as `Authorization: Bearer <token>` header on protected routes.

---

## Health

### `GET /health`
Check API is alive.
**Auth:** None
**Response:**
```json
{ "success": true, "data": { "status": "ok", "version": "1.0.0" }, "error": null }
```

---

## Users

### `POST /users`
Create a new user account when they first enter their Letterboxd username.
**Auth:** None (creates account)
**Request:**
```json
{
  "letterboxd_username": "string",          // required
  "serializd_username": "string",           // optional
  "country_code": "IN",                     // optional, ISO 3166-1 alpha-2
  "preferred_format": "both"               // optional: 'films' | 'shows' | 'both'
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "letterboxd_profile": {
      "username": "string",
      "display_name": "string",
      "avatar_url": "string",
      "is_private": false
    },
    "sync_status": "pending"
  }
}
```
**Errors:**
- `PROFILE_PRIVATE` — Letterboxd profile is private
- `PROFILE_NOT_FOUND` — username doesn't exist on Letterboxd
- `SCRAPE_FAILED` — could not reach Letterboxd

---

### `GET /users/:user_id`
Get user profile and sync status.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "letterboxd_username": "string",
    "serializd_username": "string | null",
    "country_code": "string",
    "preferred_format": "string",
    "last_synced_at": "ISO string | null",
    "sync_status": "complete",
    "total_films_watched": 312,
    "has_taste_profile": true,
    "streaming_services": [
      { "provider_id": 8, "provider_name": "Netflix" }
    ]
  }
}
```

---

### `PATCH /users/:user_id`
Update user preferences.
**Auth:** Required
**Request:**
```json
{
  "country_code": "string",
  "preferred_format": "string",
  "display_name": "string"
}
```
**Response:** Updated user object (same shape as GET)

---

### `POST /users/:user_id/streaming-services`
Set which streaming services the user subscribes to. Replaces existing list.
**Auth:** Required
**Request:**
```json
{
  "provider_ids": [8, 9, 337]               // TMDB provider IDs
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "services": [
      { "provider_id": 8, "provider_name": "Netflix" },
      { "provider_id": 9, "provider_name": "Amazon Prime Video" },
      { "provider_id": 337, "provider_name": "Disney+" }
    ]
  }
}
```

---

## Scraping & Sync

### `POST /scrape/letterboxd`
Trigger a full or incremental scrape of a user's Letterboxd profile. Long-running — runs async. Poll sync status via GET /users/:id.
**Auth:** Required
**Request:**
```json
{
  "user_id": "uuid",
  "mode": "full"                            // 'full' | 'incremental'
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "status": "started",
    "estimated_seconds": 45
  }
}
```
**Errors:**
- `ALREADY_SYNCING` — sync already in progress for this user
- `PROFILE_PRIVATE` — profile became private

---

### `POST /scrape/serializd`
Same pattern as Letterboxd scrape but for Serializd.
**Auth:** Required
**Request/Response:** Identical shape to `/scrape/letterboxd`

---

### `GET /scrape/status/:job_id`
Poll the status of a scrape job.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "status": "enriching",                  // 'started' | 'scraping' | 'enriching' | 'profiling' | 'complete' | 'error'
    "progress": {
      "step": "Enriching film metadata",
      "films_processed": 145,
      "films_total": 312
    },
    "error": null
  }
}
```

---

## Taste Profile

### `GET /profile/:user_id`
Get the user's full taste profile.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "taste_summary": "string",
    "taste_fingerprint": "string",
    "top_genres": [
      { "genre": "Drama", "avg_rating": 4.2, "count": 87 }
    ],
    "preferred_eras": [
      { "decade": "1990s", "avg_rating": 4.4 }
    ],
    "tone_profile": {
      "dark_light": -0.4,
      "slow_fast": -0.6,
      "emotional_intellectual": 0.2,
      "arthouse_mainstream": -0.3
    },
    "narrative_preference": "character",
    "pacing_preference": "slow_burn",
    "ending_preference": "ambiguity",
    "top_directors": ["Denis Villeneuve", "Paul Thomas Anderson"],
    "top_cinematographers": ["Roger Deakins", "Hoyte van Hoytema"],
    "top_composers": ["Jonny Greenwood", "Ennio Morricone"],
    "invisible_preferences": [
      "You consistently rate films higher when runtime exceeds 2 hours",
      "Your highest-rated films almost always feature non-linear narratives"
    ],
    "negative_signals": [
      "Jump-scare horror consistently underperforms in your ratings",
      "Ensemble comedies rarely score above 3 stars for you"
    ],
    "emotional_aftertastes": [
      { "emotion": "melancholy", "correlation_score": 0.82 },
      { "emotion": "awe", "correlation_score": 0.74 }
    ],
    "pretension_score": -0.3,
    "blind_spots": {
      "decades": ["1960s", "1970s"],
      "countries": ["South Korea", "Romania"],
      "genres": ["Westerns", "Musicals"]
    },
    "films_analyzed": 312,
    "profile_version": 3,
    "updated_at": "ISO string"
  }
}
```
**Errors:**
- `PROFILE_NOT_READY` — taste profile hasn't been generated yet

---

### `POST /profile/:user_id/regenerate`
Force a full taste profile regeneration from existing watch history. Use sparingly.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": { "job_id": "uuid", "status": "started" }
}
```

---

## Recommendations

### `GET /recommendations/:user_id`
Get personalized film/show recommendations.
**Auth:** Required
**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `format` | string | `both` | `films` \| `shows` \| `both` |
| `mood` | string | null | free text mood input |
| `mood_preset` | string | null | `comfort` \| `cry` \| `disturb` \| `date_night` \| `group` \| `focus` \| `celebrate` \| `decompress` |
| `max_runtime` | integer | null | max runtime in minutes |
| `min_runtime` | integer | null | min runtime in minutes |
| `provider_ids` | string | null | comma-separated TMDB provider IDs to filter by |
| `hidden_gems` | boolean | false | only return low-popularity picks |
| `include_wild_card` | boolean | true | include one wild card pick |
| `include_anti_recs` | boolean | false | include anti-recommendations |
| `limit` | integer | 10 | number of main recs (max 20) |

**Response:**
```json
{
  "success": true,
  "data": {
    "recommendations": [
      {
        "film": {
          "tmdb_id": 12345,
          "media_type": "film",
          "title": "Annihilation",
          "release_year": 2018,
          "runtime_minutes": 115,
          "genres": ["Sci-Fi", "Horror", "Drama"],
          "directors": ["Alex Garland"],
          "poster_path": "/path.jpg",
          "tmdb_rating": 7.4,
          "overview": "string"
        },
        "reason": "You'll recognize the same slow dread and unreliable reality that made Hereditary your 5-star pick — except here it's laced with scientific wonder you responded to so strongly in Arrival.",
        "confidence": "high",
        "tags": ["slow burn", "atmospheric", "unreliable narrator", "female-led"],
        "streaming": [
          { "provider_id": 9, "provider_name": "Amazon Prime Video", "type": "subscription" }
        ],
        "predicted_rating": 4.5,
        "is_wild_card": false
      }
    ],
    "anti_recommendations": [
      {
        "film": { ... },
        "reason": "Despite the acclaim, you'll likely find its pacing and tonal inconsistency frustrating — the same qualities that put you off three other A-list comedies.",
        "confidence": "high"
      }
    ],
    "wild_card": {
      "film": { ... },
      "reason": "This isn't your usual territory — but your quiet appreciation for precise visual composition shows up just enough that we think you'll surprise yourself.",
      "confidence": "medium"
    },
    "generated_at": "ISO string"
  }
}
```
**Errors:**
- `PROFILE_NOT_READY` — no taste profile yet
- `INSUFFICIENT_HISTORY` — fewer than 10 films watched

---

### `GET /recommendations/:user_id/blind-spots`
Get recommendations targeting the user's cinematic blind spots.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "blind_spots": [
      {
        "type": "decade",
        "label": "You've barely explored the 1970s",
        "description": "Only 3 films in your history from this decade.",
        "entry_point": {
          "film": { ... },
          "reason": "The best entry point for your taste into 1970s cinema. The same moral ambiguity and visual patience you love is here in abundance."
        }
      },
      {
        "type": "country",
        "label": "Romanian New Wave is a gap in your history",
        "description": "Zero films from Romania, despite it producing some of the most critically lauded cinema of the 2000s.",
        "entry_point": { "film": { ... }, "reason": "..." }
      }
    ]
  }
}
```

---

### `GET /recommendations/:user_id/rabbit-hole/:tmdb_id`
Get a curated filmography rabbit hole for a director or key crew member associated with a film the user loved.
**Auth:** Required
**Query Parameters:**
| Param | Type | Description |
|---|---|---|
| `crew_type` | string | `director` \| `cinematographer` \| `composer` |
| `crew_name` | string | e.g. `Denis Villeneuve` |

**Response:**
```json
{
  "success": true,
  "data": {
    "crew_member": "Denis Villeneuve",
    "crew_type": "director",
    "intro": "You've rated 3 of his 7 feature films. Here's the ideal order to complete the journey.",
    "filmography": [
      {
        "film": { ... },
        "watched": true,
        "user_rating": 5.0,
        "recommended_order": 1,
        "order_reason": "Start here if you haven't — it's the clearest entry to his style"
      }
    ]
  }
}
```

---

### `GET /recommendations/:user_id/debate-picks`
Get films specifically chosen to spark discussion and debate.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "picks": [
      {
        "film": { ... },
        "debate_reason": "Its ending has been interpreted at least four different ways by serious critics. You'll have opinions.",
        "divisiveness_score": 0.84
      }
    ]
  }
}
```

---

## Watchlist

### `GET /watchlist/:user_id`
Get user's watchlist, optionally ranked by AI.
**Auth:** Required
**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `ranked` | boolean | false | return AI-ranked order |
| `mood` | string | null | factor mood into ranking |

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 47,
    "items": [
      {
        "film": { ... },
        "rank": 1,
        "rank_reason": "Best match for your current mood and it's leaving Netflix in 5 days.",
        "streaming": [ ... ],
        "added_at": "ISO string"
      }
    ]
  }
}
```

---

### `POST /watchlist/:user_id`
Add a film to the watchlist manually.
**Auth:** Required
**Request:**
```json
{ "tmdb_id": 12345, "media_type": "film", "notes": "optional note" }
```
**Response:** The created watchlist item.

---

### `DELETE /watchlist/:user_id/:film_id`
Remove a film from the watchlist.
**Auth:** Required
**Response:** `{ "success": true, "data": { "deleted": true } }`

---

## Compatibility

### `POST /compatibility`
Analyze taste compatibility between 2–6 Letterboxd profiles.
**Auth:** Required
**Request:**
```json
{
  "initiated_by": "uuid",
  "letterboxd_usernames": ["alice", "bob", "carol"]  // 2–6 usernames
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "profiles": [
      { "username": "alice", "display_name": "Alice", "avatar_url": "..." }
    ],
    "overlap_score": 74.2,
    "shared_traits": [
      "All prefer slow-paced atmospheric films",
      "Strong agreement on 2010s American independent cinema"
    ],
    "divergence_points": [
      "alice and bob disagree sharply on horror — bob rates it highly, alice avoids it"
    ],
    "recommended_films": [
      { "film": { ... }, "reason": "Highest probability of everyone enjoying this." }
    ],
    "bridge_pick": { "film": { ... }, "reason": "..." },
    "compromise_pick": { "film": { ... }, "reason": "Nobody's first choice, but nobody will hate it." }
  }
}
```
**Errors:**
- `TOO_FEW_PROFILES` — fewer than 2 usernames provided
- `TOO_MANY_PROFILES` — more than 6 usernames provided
- `PROFILE_NOT_FOUND` — one or more usernames don't exist on Letterboxd

---

## Film Twin

### `GET /twin/:user_id`
Find the user's closest taste match on the platform.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "twin": {
      "user_id": "uuid",
      "letterboxd_username": "string",
      "similarity_score": 0.923,
      "shared_traits": [
        "Both prefer slow-burn thrillers",
        "Both rate Denis Villeneuve's work 4.5+ consistently"
      ]
    },
    "recommendations_from_twin": [
      {
        "film": { ... },
        "twin_rating": 5.0,
        "reason": "Your film twin's highest-rated film you haven't seen."
      }
    ]
  }
}
```
**Errors:**
- `NO_TWIN_FOUND` — not enough users on platform yet for matching
- `PROFILE_NOT_READY` — user's own taste profile not ready

---

## Predictions

### `POST /predictions`
Create a pre-watch rating prediction.
**Auth:** Required
**Request:**
```json
{ "user_id": "uuid", "tmdb_id": 12345, "media_type": "film" }
```
**Response:**
```json
{
  "success": true,
  "data": {
    "prediction_id": "uuid",
    "predicted_rating": 4.0,
    "confidence": "high",
    "prediction_reason": "Based on 6 comparable films in your history, this director's style, and your response to similar pacing."
  }
}
```

---

### `PATCH /predictions/:prediction_id`
Report the actual rating after watching.
**Auth:** Required
**Request:**
```json
{ "actual_rating": 4.5 }
```
**Response:**
```json
{
  "success": true,
  "data": {
    "prediction_id": "uuid",
    "predicted_rating": 4.0,
    "actual_rating": 4.5,
    "delta": 0.5,
    "accuracy_message": "We were 0.5 stars off. Not bad."
  }
}
```

---

### `GET /predictions/:user_id/accuracy`
Get overall prediction accuracy stats for a user.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "total_predictions": 23,
    "resolved_predictions": 18,
    "avg_delta": 0.42,
    "within_half_star": 0.72,
    "within_one_star": 0.89,
    "accuracy_message": "We've predicted your rating within 0.5 stars 72% of the time."
  }
}
```

---

## Post-Watch Reflection

### `POST /reflections`
Submit a post-watch reflection.
**Auth:** Required
**Request:**
```json
{
  "user_id": "uuid",
  "tmdb_id": 12345,
  "media_type": "film",
  "stayed_with_you": "The ending stayed with me for days — that silence was devastating.",
  "would_change": "The second act felt slightly slow compared to the first."
}
```
**Response:**
```json
{
  "success": true,
  "data": { "reflection_id": "uuid", "processed": false }
}
```

---

## Taste Challenges

### `GET /challenges/:user_id`
Get the current week's challenge for a user.
**Auth:** Required
**Response:**
```json
{
  "success": true,
  "data": {
    "challenge_id": "uuid",
    "challenge_type": "new_country",
    "challenge_text": "Watch a film from a country you've never explored. Here's where to start.",
    "week_of": "2025-01-06",
    "suggested_film": { ... },
    "completed": false
  }
}
```

---

### `POST /challenges/:challenge_id/complete`
Mark a challenge as complete.
**Auth:** Required
**Request:**
```json
{ "completed_with_tmdb_id": 12345, "media_type": "film" }
```
**Response:**
```json
{
  "success": true,
  "data": { "challenge_id": "uuid", "completed": true, "completed_at": "ISO string" }
}
```

---

## Error Codes Reference

| Code | HTTP Status | Meaning |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid auth token |
| `FORBIDDEN` | 403 | Token valid but no permission |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `PROFILE_NOT_FOUND` | 404 | Letterboxd/Serializd username not found |
| `PROFILE_PRIVATE` | 403 | Letterboxd profile is private |
| `PROFILE_NOT_READY` | 202 | Taste profile still being generated |
| `INSUFFICIENT_HISTORY` | 422 | Too few films watched to generate profile |
| `ALREADY_SYNCING` | 409 | Sync already in progress |
| `SCRAPE_FAILED` | 502 | Scraper could not reach the source |
| `SCRAPE_BLOCKED` | 503 | Scraper was rate-limited or blocked |
| `AI_FAILED` | 502 | LLM call failed |
| `TOO_FEW_PROFILES` | 422 | Compatibility needs at least 2 profiles |
| `TOO_MANY_PROFILES` | 422 | Compatibility max is 6 profiles |
| `NO_TWIN_FOUND` | 404 | No matching twin found on platform |
| `RATE_LIMITED` | 429 | Too many requests from this user |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
