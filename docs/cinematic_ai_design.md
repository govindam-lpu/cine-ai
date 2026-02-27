# CinematicAI — Design Document
### Visual Identity, UI System & UX Architecture

---

## Design Philosophy

CinematicAI is not a utility. It's a mirror — it reflects who you are as a viewer. The design should feel like stepping into a private, dimly lit film archive that was built specifically for you. It should feel **curated, personal, and a little cinematic itself.**

The aesthetic direction is: **Dark editorial minimalism with warmth.**

Think of a high-end film journal crossed with a Criterion Collection catalogue. Quiet confidence. No noise. Every element earns its place. The UI should feel like it was designed by someone who loves cinema deeply — not a SaaS dashboard with a movie skin on top.

**The one thing users will remember:** The moment they see their Taste DNA card for the first time and think *"this is actually me."*

---

## Aesthetic Direction

**Mood board in words:**
- A24 opening titles
- Criterion Collection spine typography
- The silence before a film starts
- Warm tungsten light in a dark room
- A worn notebook full of handwritten film notes
- The moment a great film poster stops you in your tracks

**What this means in design terms:**
- Dark backgrounds, not pitch black — a very deep warm charcoal
- Warm accent colors, not cold blues or purple gradients
- Serif typography for display / personality — not another grotesque sans-serif app
- Generous whitespace (breathing room = prestige)
- Film grain texture as a subtle background layer
- No rounded pill buttons — sharp or very slightly rounded corners only
- Poster art as the primary visual content — let the films do the visual work

---

## Color System

```css
:root {
  /* Backgrounds */
  --bg-void:        #0D0C0B;   /* Deepest background — almost black, warm undertone */
  --bg-base:        #141210;   /* Primary page background */
  --bg-surface:     #1C1A18;   /* Cards, panels, modals */
  --bg-elevated:    #242220;   /* Hover states, elevated cards */
  --bg-overlay:     #2C2A27;   /* Tooltips, dropdowns */

  /* Text */
  --text-primary:   #F0EBE3;   /* Main readable text — warm white, not pure white */
  --text-secondary: #A09890;   /* Subtitles, metadata, labels */
  --text-muted:     #5C5550;   /* Placeholder, disabled */
  --text-inverse:   #0D0C0B;   /* Text on light backgrounds */

  /* Accent — the signature color */
  --accent:         #E8C547;   /* Warm amber/gold — a film reel in lamplight */
  --accent-dim:     #A8903A;   /* Muted accent for hover or secondary use */
  --accent-glow:    rgba(232, 197, 71, 0.12); /* Ambient glow for cards */

  /* Semantic */
  --positive:       #7EC87A;   /* Good match, high confidence */
  --warning:        #E8A047;   /* Medium confidence, wild card */
  --negative:       #C86060;   /* Anti-recommendation, low match */

  /* Borders */
  --border-subtle:  rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-accent:  rgba(232, 197, 71, 0.30);
}
```

**Color Usage Rules:**
- Never use pure `#000000` or `#FFFFFF` — always warm near-blacks and near-whites
- The amber accent (`--accent`) is used sparingly — only for the most important interactive elements, highlights, and the Taste DNA card
- Use transparency and layering, not flat fills, for most surfaces
- Film posters provide most of the color variety on screen — the UI frames them, not competes with them

---

## Typography

### Font Pairing

**Display / Headings: `Playfair Display`**
A high-contrast serif with editorial personality. Used for feature headings, the app name, section titles, and the Taste DNA summary text. It carries cinematic weight without feeling old-fashioned.

**Body / UI: `DM Sans`**
Clean, slightly warm geometric sans-serif. Not Inter. Comfortable at small sizes for metadata and readable at medium sizes for descriptions. The contrast with Playfair Display creates a sophisticated editorial feel.

**Monospace / Data: `JetBrains Mono`**
Used only for small data labels like rating numbers, match percentages, and year metadata. Adds a subtle technical-archival quality to stats.

```css
/* Import */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-display: 'Playfair Display', Georgia, serif;
  --font-body:    'DM Sans', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;
}
```

### Type Scale

```css
--text-xs:    11px;   /* Micro labels, tags */
--text-sm:    13px;   /* Secondary metadata */
--text-base:  15px;   /* Body copy */
--text-md:    17px;   /* Card descriptions */
--text-lg:    21px;   /* Section subheadings */
--text-xl:    28px;   /* Section headings (DM Sans) */
--text-2xl:   38px;   /* Page titles (Playfair) */
--text-3xl:   54px;   /* Hero headings (Playfair) */
--text-4xl:   72px;   /* App name / splash (Playfair) */
```

### Typography Rules
- Display headings (`--font-display`) are always used at `--text-2xl` and above
- Body and UI text always uses `--font-body`
- Ratings, years, percentages always use `--font-mono`
- Never bold body copy — use weight `500` for emphasis
- Line height for body: `1.65`. For headings: `1.15`
- Letter spacing for all-caps labels: `0.12em`

---

## Texture & Atmosphere

The background of every screen has a very subtle film grain texture layered over it. This is a `noise.png` or SVG filter applied at low opacity — it adds analog warmth and prevents the dark background from feeling sterile.

```css
/* Film grain overlay — applied globally */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url('/textures/grain.png');
  background-repeat: repeat;
  opacity: 0.032;
  pointer-events: none;
  z-index: 9999;
}
```

Additionally, a very faint radial gradient vignette at the edges of the viewport on most pages — reinforces the "sitting in a dark room" feeling.

---

## Spacing System

Based on an 8px base unit. Every spacing value in the app is a multiple of 4px.

```css
--space-1:  4px
--space-2:  8px
--space-3:  12px
--space-4:  16px
--space-5:  20px
--space-6:  24px
--space-8:  32px
--space-10: 40px
--space-12: 48px
--space-16: 64px
--space-20: 80px
--space-24: 96px
```

**Guiding rule:** When in doubt, add more space. Prestige products breathe.

---

## Component Library

### Film Card (Primary)

The most repeated component in the app. Two variants: **Compact** and **Feature**.

**Compact Card** (used in grid recommendations)
```
┌────────────────────┐
│                    │
│   [POSTER IMAGE]   │  ← 2:3 ratio, fills card width
│                    │
│ ████ Title         │  ← Playfair Display, 15px
│ 2019 · Drama · 2h  │  ← DM Sans, 12px, --text-secondary
│ ★ 4.2              │  ← JetBrains Mono, amber color
│                    │
│ "Because you loved │  ← Reason text, italic, 12px
│  the cinematog..." │
│                    │
│ [Netflix] [+List]  │  ← Streaming badge + action
└────────────────────┘
```

- Poster is the hero — minimum 60% of card height
- On hover: card lifts with a `box-shadow` using `--accent-glow`
- A thin top border in `--border-accent` appears on hover
- No heavy rounded corners — `border-radius: 4px` maximum

**Feature Card** (used in spotlight / top pick)
- Full-width or half-width
- Poster on the left, all details on the right
- Larger typography, full "why you'll like this" text visible
- Match confidence badge visible (not just on hover)

---

### Taste DNA Card

The signature component. Feels like a physical card — almost like a concert ticket or Criterion spine.

```
┌─────────────────────────────────────────────────┐
│  C I N E M A T I C A I          [username]      │
│ ─────────────────────────────────────────────── │
│                                                  │
│  "You're an atmosphere-first viewer who trusts  │
│   silence more than exposition. You seek         │
│   emotional authenticity above plot mechanics." │
│                                                  │
│  ─────────────────────────────────────────────  │
│                                                  │
│  TOP GENRES          FAVORITE ERA               │
│  Drama 42%           1970s – 1990s              │
│  Thriller 28%                                   │
│  Horror 18%          PRETENSION SCORE           │
│                      ████████░░  Independent    │
│  ─────────────────                              │
│                      CREW AFFINITIES            │
│  TONE PROFILE        Denis Villeneuve           │
│  [radar chart]       Roger Deakins              │
│                      Ennio Morricone            │
│                                                  │
│  ─────────────────────────────────────────────  │
│  cinematicai.com                    [share ↗]   │
└─────────────────────────────────────────────────┘
```

- Background: a very subtle gradient using the user's most-watched genre colors
- The summary text uses Playfair Display italic — it should feel like a film review about the user
- Exportable as a PNG (like Spotify Wrapped)
- Accent gold border `1px` around the entire card
- The radar chart is minimal — thin lines, gold fills, dark background

---

### Confidence Badge

Small pill label attached to each recommendation indicating match confidence.

```
[● HIGH MATCH]      → --positive color, subtle bg
[◐ LIKELY]          → --warning color, subtle bg
[◌ WILD CARD]       → --accent color, subtle bg, dashed border
```

All uppercase, `--text-xs`, `--font-body` weight 500, letter spacing `0.1em`.

---

### Mood Selector

A horizontal scroll of mood chips on the recommendation page. Not dropdown — always visible.

```
 [Comfort Watch]  [Need to Cry]  [Can't Focus]  [Date Night]  [Want to Think]  [Disturb Me]
```

- Inactive: `--bg-surface` fill, `--border-default` border, `--text-secondary` text
- Active: `--accent` border, `--accent-glow` background, `--text-primary` text
- Subtle scale transform on hover: `scale(1.03)`
- Sharp corners: `border-radius: 3px`

---

### Streaming Badge

Small icons showing where a film is currently available.

- Tiny platform logo (16x16px)
- Tooltip on hover with platform name
- Greyed out if the user doesn't subscribe to that service
- "Not streaming" shown as a subtle `--text-muted` label — not hidden

---

### Progress / Loading State

Since scraping and AI analysis takes time, the loading state is a first-class experience:

```
Fetching your Letterboxd history...       ✓
Enriching with film metadata...           ✓
Identifying taste patterns...             ● (animated)
Building your profile...
```

- Line-by-line reveal with a typewriter effect
- Each completed step gets a warm amber checkmark
- The active step has a slow pulse animation
- Underneath: a randomly rotating film still from a well-known cinematic scene (blurred, used as atmosphere only)
- Feels like it's doing real work — because it is

---

## Page-by-Page Design

### Landing Page

**Layout:** Full viewport. Centered. Sparse.

```
[full screen — dark, grain texture, vignette edges]

        CINEMATICAI

  Film recommendations that know you.
  Not what you watched. Who you are.

  [ Enter your Letterboxd username ]

                [→ Build My Profile]

  Trusted by taste. Not an algorithm.
```

- App name in Playfair Display, `--text-4xl`, all caps, tracked wide
- Tagline in DM Sans light, `--text-lg`, `--text-secondary`
- Input field: bottom border only (no box), `--accent` color on focus
- CTA button: flat, `--accent` background, `--text-inverse` text, no rounded corners
- Below the fold: subtle horizontal scroll of film posters (blurred, low opacity) as ambient texture
- No hero image. No illustration. No gradient blob. The restraint is the statement.

---

### Onboarding / Profile Build Page

Three clean steps shown as a horizontal progress line (not a wizard with back/next buttons — feels linear and confident).

**Step 1 — Connect**
Username input for Letterboxd + optional Serializd. Clean, one thing at a time.

**Step 2 — Loading** (the typewriter loading experience described above)

**Step 3 — First Reveal**
The Taste DNA card animates in. Before any recommendations. This is the emotional hook — let it land. Simple CTA: "Now find me something to watch →"

---

### Recommendations Page (Main Dashboard)

**Layout:** Two-column on desktop (sidebar left, content right). Single column on mobile.

**Left Sidebar (220px)**
```
[Avatar + username]
[Taste DNA — mini card]

FILTER
─────────────
Format
 ○ Films  ○ Shows  ● Both

Mood
 [mood chips — vertical]

Streaming
 ☑ Netflix  ☑ Prime
 ☑ MUBI    ☐ Apple TV

Runtime
 [slider: 60min — 3hr+]

Genre
 [tag cloud — user's top genres]

Advanced
 [Hidden Gems mode toggle]
 [Wild Card toggle]
```

**Right Content Area**
- Top: one Feature Card (the top pick, larger treatment)
- Below: grid of 4 Compact Cards (2x2 on desktop)
- Below that: "More picks" — another row of 4
- At bottom: special sections with their own visual treatment:
  - "Your Blind Spots" section
  - "Don't Bother" (anti-recs) — slightly different visual, `--negative` accent
  - "This Week's Wild Card" — dashed border card, stands apart

**Refresh behavior:** Clicking "Find me something different" reshuffles recommendations with a smooth stagger animation. Doesn't hard reload.

---

### Taste DNA Page (Full View)

Full page expansion of the Taste DNA card. Broken into sections:

- **The Summary** — full paragraph, large Playfair italic, centered, max-width 640px
- **Tone Radar Chart** — centered, large, interactive (hover shows dimension labels)
- **Genre Breakdown** — horizontal bar chart, warm amber fills
- **Invisible Preferences** — list of non-obvious detected patterns, each as a small card
- **Crew Affinities** — director/DP/composer names in a tag-cloud style layout
- **Taste Evolution Timeline** — a horizontal scrollable year-by-year summary
- **Pretension Score** — a single horizontal slider showing where they fall on the spectrum, with a label
- **Export Card** button — generates the shareable PNG card

---

### Compatibility Mode Page

Clean two-pane layout. Each profile on one side.

```
[User A — mini DNA card]     [User B — mini DNA card]
              ↕ COMPATIBILITY ANALYSIS ↕
       [Overlap radar — two overlaid profiles]

THEY'LL BOTH LOVE        WHERE THEY CLASH
──────────────────        ──────────────────
[3 shared recs]           [divergence breakdown]

        [THE BRIDGE PICK — 1 prominent card]
```

---

### Watchlist Ranker Page

Simple ranked list. Numbered. Clear.

```
YOUR WATCHLIST — RANKED FOR TONIGHT

1.  [poster]  Film Title                    [Netflix]
              "Best match for your current mood"   ★ 4.7

2.  [poster]  Film Title                    [MUBI]
              "You'll love the cinematographer"    ★ 4.4

...

47. [poster]  Film Title                    [Not streaming]
              "Save this for when you're ready"
```

Drag to reorder. Tap to see full recommendation reason.

---

### Film Twin Page

```
YOUR FILM TWIN

[Avatar placeholder]  ←→  [Avatar placeholder]
  @username                  @twin_username

TASTE OVERLAP: 89%

TOP 3 SHARED TRAITS
── Prefers atmospheric over plot-driven
── High tolerance for slow burn
── Rates arthouse above mainstream average

THEY'VE SEEN. YOU HAVEN'T.
[grid of 6 compact cards]
```

---

## Motion & Animation Principles

**Guiding rule:** Motion should feel like a film — purposeful cuts, no flicker, no bounce.

- **Entry animations:** Fade up (`opacity 0→1` + `translateY 12px→0`), duration `400ms`, ease `cubic-bezier(0.16, 1, 0.3, 1)`
- **Stagger:** Card grids stagger in at `60ms` per card
- **Hover:** Cards lift with `translateY(-3px)` + `box-shadow` change — `200ms ease`
- **Page transitions:** Cross-fade at `250ms` — no slide transitions (too app-like, not cinematic)
- **Loading typewriter:** Character by character at `30ms/char`, line by line
- **DNA card reveal:** Scale from `0.94 → 1.0` + fade, `600ms`, delayed entrance for each section
- **No bounce.** No spring physics. Film doesn't bounce.

---

## Iconography

Use **Phosphor Icons** (thin weight). They're refined, slightly editorial, and less generic than Lucide or Heroicons.

Key icons used:
- `FilmStrip` — app mark / favicon
- `Star` — ratings
- `Eye` — watched
- `EyeSlash` — not watched / hidden gems
- `ArrowsLeftRight` — compatibility
- `Shuffle` — wild card
- `BookmarkSimple` — watchlist
- `ChartBar` — taste DNA
- `Users` — friends / twins
- `Export` — share card

Icon sizes: `16px` (inline), `20px` (UI actions), `24px` (navigation).

---

## Responsive Breakpoints

```css
--mobile:   < 640px    /* Single column, bottom nav */
--tablet:   640–1024px /* Simplified sidebar, 2-col grid */
--desktop:  > 1024px   /* Full two-column layout */
--wide:     > 1400px   /* Max-width container: 1280px, centered */
```

Mobile nav: bottom tab bar with 4 icons: Home, Taste DNA, Compatibility, Profile. No hamburger menu.

---

## Dark Mode Only

This app is dark mode only. There is no light mode. The experience is designed for darkness — like a cinema.

If a user's OS is in light mode, they still see the dark UI. A small note in settings: *"CinematicAI is designed for the dark."*

---

## Naming & Voice

The app's voice is:
- **Intelligent, not condescending**
- **Specific, not generic** — never say "based on your preferences," say "because you gave Denis Villeneuve three 5-star ratings"
- **Honest** — the anti-recommendation feature tells the truth, not what the user wants to hear
- **Personal** — uses second person everywhere: "you," "your taste," "you'll notice"

Microcopy examples:
- Empty watchlist: *"Nothing saved yet. Every great film library starts somewhere."*
- First load: *"Building your taste profile. This only happens once."*
- Anti-rec: *"Honest takes. Skip this one."*
- Wild card: *"This one surprised us too. Give it 20 minutes."*
- Blind spot: *"You've barely touched this corner of cinema. Here's where to start."*
- No streaming match: *"Worth finding. It's not on your services right now."*

---

## Logo & App Mark

**Wordmark:** CINEMATICAI — Playfair Display, all caps, moderate tracking (`0.15em`). The "AI" has a very subtle amber color distinguishing it from the rest.

**App Mark (icon):** A single film frame — a square with two perforations on each side, containing a minimal abstract representation of a play symbol. Works at 16px favicon size and 512px app store size. Amber on dark.

---

## What This Design is NOT

To stay true to the vision, explicitly avoid:

- Purple or blue gradients on dark backgrounds (tired AI aesthetic)
- Rounded pill buttons everywhere
- Generic sans-serif only (Inter, Roboto, system fonts)
- Bright white cards on dark backgrounds (too high contrast, too harsh)
- Oversized hero illustrations
- Confetti, sparkles, or playful illustrations — this is a serious tool for serious viewers
- Dashboard-style metric boxes everywhere
- Anything that looks like it was designed to look like Netflix

---

## Summary — Design in One Sentence

A dark, grain-textured editorial interface that frames film art and surfaces personal insight with the quiet confidence of a cinephile who has seen everything — and knows exactly what you should watch next.

---

*End of Design Document*
