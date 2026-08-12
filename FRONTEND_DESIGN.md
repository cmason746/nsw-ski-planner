# Frontend Design

> The visual/layout design for the React frontend. The **interaction flow** lives
> in [ARCHITECTURE.md](ARCHITECTURE.md) → "App flow (user journey)"; this doc is
> the **visual layer** — how each screen looks and lays out. Present tense,
> updated as decisions are made.
>
> Status: **design agreed, not yet mocked up or built.** Nothing here is coded.

## Shape of the app

Two in-app **views (tabs) you can flick between without losing state**:

1. **Overview** — the neutral, preference-independent conditions view (default).
2. **Recommendation** — the ranked result cards, populated after preferences are set.

Switching to Recommendation does **not** discard the Overview — the user can flick
back and forth. These are in-app view toggles, **not** browser tabs.

> This refines the earlier "single scrolling page … cards below" line in
> ARCHITECTURE.md: the recommendation now lives in its own view, so the overview
> stays intact while you read the recommendation.

## Overview view

Three resort **sections stacked vertically**, one per resort (Perisher, Thredbo,
Selwyn). Goal: all three sections visible together, so each section stays a
compact horizontal band.

**Why stacked-by-resort (not a big comparison grid):** across the few days a user
picks, the *weather* forecast doesn't differ much between the three resorts — so
the overview's job isn't "compare resort A vs B on weather", it's "is this weekend
good, and which **day** is best." The resort differentiation comes mostly from the
static characteristics + the recommendation.

### Per resort section

```
PERISHER            38/45 lifts · 96 cm base · largest resort · medium runs
 ┌─ Thu 13 ─┐  ┌─ Fri 14 ─┐  ┌─ Sat 15 ─┐  ┌─ Sun 16 ─┐   →  (scrolls sideways)
 │ AM │ PM  │  │ AM │ PM  │  │ ...      │  │ ...      │
 │ …headline│  │ …headline│  │          │  │          │
 │    [+]   │  │    [+]   │  │   [+]    │  │   [+]    │
 └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

- **Resort heading** carries the **static, per-resort snapshot** that doesn't
  change day to day: open-lift count/%, base depth, and the character words
  (size / run length / terrain). These are *not* repeated on each day-card.
- **Day-cards laid out in a horizontal row**, one per picked day. Many days →
  **horizontal scroll** (accepted: users rarely pick a long range; if they do,
  they scroll). Keeps each resort a compact band so all three fit vertically.

### Per day-card

- **Headline: three key dot-points** at the top for an at-a-glance read.
  - **Which three factors headline, and their order, is still to be decided by
    Charlotte** (see Open decisions). Candidates discussed: sunniness, snow, wind.
  - The headline **flexes with conditions** — it can't always be the same three:
    when it's **snowing**, sunniness is N/A (per the scoring rule); when it's
    **dry**, there's no snowfall figure. So the card needs headline *slots* that
    swap what fills them, not three hard-coded factors.
- **Split into AM / PM as two columns** — mirrors the `am`/`pm` windows in the
  data model.
- **Expandable via a `+` at the bottom** — collapsed shows the headline; expand to
  drill into the full per-window weather. Same summary→expand pattern as the
  recommendation cards, for one consistent interaction across the app.
- **Recent snow is included** in the overview (per-day). *(Decided — earlier we'd
  considered leaving it out; it's in.)*

## Preferences

- Entered via a **prominent, catchy button** near the top ("what matters to you?"
  style) that opens a **modal**. Not an auto-firing popup — the user chooses when.
- The button needs to be visually inviting so users *want* to press it (styling
  TBD at mockup time).
- The question set itself is already defined in ARCHITECTURE.md → "User inputs &
  weighting" (ability, cost, bigger resort, longer runs, snowy/bluebird; beginners
  asked only about cost).
- On submit → calls `POST /recommend`, populates the Recommendation view, switches
  to it.

## Recommendation view

- The ranked **result cards** — best resort per day, top 3, one card per day.
- **Expandable cards**: collapsed summary (rank, resort, day, headline) → expand
  for the full "why" prose (from the backend). Detailed content spec already in
  ARCHITECTURE.md → Scoring "Explanation" (#6).
- Lives in its own view; flick back to Overview any time.

## Data source

Both views are driven by the live backend (see [CLAUDE.md](CLAUDE.md) → Deployment):
- Overview ← `GET /conditions`
- Recommendation ← `POST /recommend`
- Date picker capped at **10 days** out (forecast horizon).

## Open decisions (ask Charlotte)

- **Headline factors for the day-card:** which factors fill the three headline
  slots, in what order, and the rule for what swaps in/out by condition
  (e.g. is wind always shown, or only when high?).
- Preferences button copy + styling (at mockup time).
- Visual style overall — colours, typography, density, icon set for the weather
  factors (`overview.py` deliberately leaves icon choice to the frontend).
