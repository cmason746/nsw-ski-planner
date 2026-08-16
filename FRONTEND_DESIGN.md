# Frontend Design

> The visual/layout design for the React frontend. The **interaction flow** lives
> in [ARCHITECTURE.md](ARCHITECTURE.md) → "App flow (user journey)"; this doc is
> the **visual layer** — how each screen looks and lays out. Present tense,
> updated as decisions are made.
>
> Status: **design agreed and mocked up; not yet built in React.** Throwaway HTML
> mockups exist — `mockups/overview.html` and `mockups/recommendation.html` (open in a
> browser; fake data shaped like the real API). They are the visual reference for the
> build. Nothing is coded in the actual `frontend/` app yet.

## Name & identity

- **App name: Snowbound.** Tagline: *"Your guide to NSW's ski resorts."* Shown large,
  top-left of every view.

## Shape of the app

Two in-app **views (tabs) you can flick between without losing state**:

1. **Conditions Overview** — the neutral, preference-independent conditions view (default).
2. **Resort Recommendation** — the ranked result cards, populated after preferences are set.

(Tab labels are the full "Conditions Overview" / "Resort Recommendation" — clearer than
the bare words.)

Switching to Recommendation does **not** discard the Overview — the user can flick
back and forth. These are in-app view toggles, **not** browser tabs.

> This refines the earlier "single scrolling page … cards below" line in
> ARCHITECTURE.md: the recommendation now lives in its own view, so the overview
> stays intact while you read the recommendation.

## Component architecture (React build)

The build is a **mockup → React translation** (the two files in `mockups/` are the
visual + logic reference). Agreed structure:

**Styling: CSS Modules** — each component has its own `*.module.css` (scoped class
names, no global collisions); the shared palette/shape tokens live once in
`src/lib/tokens.css` as CSS variables. No Tailwind, no global stylesheet sprawl.

**State model:** all shared state lives in `App.jsx` and flows down as props — no
Redux, no router (the app is two in-app views). Both views stay **mounted**; the
inactive one is `hidden`, so scroll position / expanded cards survive tab switches.
State: `activeTab`, `conditions` (GET /conditions), `dateRange`, `prefs` (null
until the wizard finishes), `recommendation` (POST /recommend). Data state is added
as each wiring step lands, not all up front.

```
src/
  main.jsx
  App.jsx                    shell: top bar, tab switch, owns shared state
  lib/
    tokens.css               design tokens (colours, radius, shadow)
    iconMap.js               ICONS name→[Lucide component, colour] + icon-name helpers
    Icon.jsx                 <Icon name color size> — renders one Lucide icon
    overviewFormat.js        ORDER, dayType, factorParts, sunIcon (overview logic)
    recommendFormat.js       numUnit, shortRS, factValLab, chip (recommend logic)
    dates.js                 prettyDate + date-range helpers
  api/client.js              getConditions(), postRecommend(prefs)
  components/
    TopBar.jsx               brand + tagline + tab pill + prefs button
    DatePicker.jsx           the date pill (later: real ≤10-day calendar)
  overview/
    OverviewView.jsx         conditions → list of ResortSection
    ResortSection.jsx        resort meta chips + horizontal day-card row
    DayCard.jsx              date, recent-snow line, AM/PM grid, expand
    FactorCell.jsx           one factor cell inside the grid
  recommend/
    RecommendationView.jsx   pref bar + result cards
    PrefBar.jsx              "Your picks" chips + ✎ Edit
    ResultCard.jsx           rank + resort + chips + score, expand → why + facts
    PreferencesWizard.jsx    one-question-at-a-time modal + beginner branching
```

Build order (per CLAUDE.md TODO): shell ✓ → CORS check → Overview wired to
`GET /conditions` → wizard + Recommendation wired to `POST /recommend` → date
picker → icon pass → host. Files above are created as their step lands; the shell
ships `App`, `TopBar`, `tokens.css`, and placeholder Overview/Recommendation views.

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
  change day to day: open-lift count/%, base depth, the character words
  (size / run length / terrain), and the **lift-served elevation range** shown as a
  low–high span (e.g. `1365–2037 m`) so users can read the mountain's height against
  the freezing-level rain/snow split. These are *not* repeated on each day-card.
  - API: resort object carries `elevations: { low, high }` (from `GET /conditions`).
- **Day-cards laid out in a horizontal row**, one per picked day. Many days →
  **horizontal scroll** (accepted: users rarely pick a long range; if they do,
  they scroll). Keeps each resort a compact band so all three fit vertically.

### Per day-card

Card layout, top to bottom:

1. **`recent_snow` — its own line at the very top of the card**, above the AM/PM
   table. It's a **per-day** factor (one value, same for both windows), so it doesn't
   belong in the per-window table. *(Recent snow is in the overview — decided.)*
2. **AM / PM as two columns** — mirrors the `am`/`pm` windows in the data model.
   Within each column, top to bottom:
   - **`rain_snow` always at the top**, shown **per window** (AM and PM can differ —
     e.g. snowing AM, clearing PM). Display the human-readable `rain_snow` string;
     branch layout logic on the machine `type` field, never on which keys exist.
   - **Then the top two factors shown by default**, with the rest **expandable**
     (unless there are no more to expand). The factor **order is chosen once per day**
     (see below), and **both AM and PM use that same order** — so each factor sits in
     the same grid row across the two columns and the rows line up.

   **Factor order per condition** (order = Charlotte's priority for that condition):

   | Condition | Factors, in display order |
   |---|---|
   | **snow** (all snow) | snow_amount · snow_quality · wind · sunniness · precip_probability |
   | **mix** (snow up, rain below) | snow_amount · wind · sunniness · snow_quality · precip_probability |
   | **dry** (sunny) | sunniness · wind · temperature |
   | **rain** (all rain) | precip_probability · wind · temperature · sunniness |

   **Which order a day uses — "snowiest wins":** AM and PM can be different conditions;
   the day picks a single order from the **higher-priority** of the two windows, ranked
   **snow > mix > rain > dry**. (E.g. snow AM + mix PM → snow order for both columns;
   mix AM + rain PM → mix order.) This means a day never mixes two different factor
   orders across its columns.

   **Split days (one half snows, the other doesn't) — fill the gaps:** because both
   columns share the day order, a non-snowing half may be asked for snow figures it
   doesn't have. Those cells are **filled** (muted): `snow_amount → "0cm = no new snow"`,
   `snow_quality → "–"`. Keeps every row aligned with no empty leading cells, at the
   cost of one low-info row. (Chosen over leaving blanks.)

   - **`sunniness` is present on every window type** — including snow/mix. The scorer
     drops sunniness when snowing (so powder days aren't penalised for cloud), but the
     overview shows it as honest info. `snow_amount`/`snow_quality` are real only on
     snow/mix (filled as above elsewhere). `wind` is always present; `precip_probability` is
     present only on precipitating windows (snow/mix/rain) — a **dry** window omits it (the
     backend doesn't emit it), since a chance-of-precip figure contradicts "no precipitation
     forecast" when the forecast amount is ~0.
   - **Temperature is always shown, but framed by window type.** On **snow/mix** windows the
     mid-mountain temperature is surfaced *as* `snow_quality` (temp + quality words). On
     **dry/rain** windows there's no snow to grade, so a plain `temperature` factor (🌡️) is
     shown instead — same mid-mountain window-average temp, banded **cold** (<0°C) ·
     **pleasant** (0–2°C) · **warm** (3–6°C) · **hot** (>6°C), with no snow-quality wording.
   - Expand-count: a day shows its top 2 rows; the rest expand. snow/mix days have 5
     rows (→ 3 more), rain days have 4 (→ 2 more), dry days have 3 (→ 1 more).

- **Driven by the window `type` field** (`"dry" | "snow" | "mix" | "rain"`, emitted per
  AM/PM window by `GET /conditions`). The frontend derives the **day** order from the two
  windows' types (snowiest wins) — no re-deriving the rain/snow classification itself.
- **Expandable via a `+`** — collapsed shows `rain_snow` + top 2 factor rows; expand for
  the rest. One toggle grows the whole card (both columns together). Same summary→expand
  pattern as the recommendation cards, for one consistent interaction across the app.

**Copy conventions (each factor ties the number to its meaning):**
- Factor rows read **`VALUE = descriptor`** so the figure is never bare — e.g.
  `−5°C = dry & light quality snow`, `28 km/h = fine winds`, `82% sun = sunny`,
  `9cm = decent AM snow total`. (A bare "9cm decent" was rejected as meaningless.)
- **Snow quality** labels carry the word **"quality"** and use bands
  `dry & light quality snow` / `OK quality snow` / `wet & sticky quality snow`
  (backend `_snow_quality_label`; the middle band word is **"OK"**, not "good").
- **Recent snow** shows a dash then appends the timeframe: `22cm – a bit of recent
  snow **in the past 2 days**` — makes "recent" concrete. (Frontend framing; backend
  label stays the descriptor.)
- **Precipitation** reads `85% = very likely chance of precipitation` (frontend frames
  the backend probability word as "… chance of precipitation").
- **Snow amount** names the window total so it's clearly not base/recent: `9cm =
  decent AM snow total`, `14cm = snow dump during the AM`, `2cm = dusting of snow
  during the AM` (side = AM/PM). Mix windows append the note `· rain below ~X m`.

**AM/PM alignment:** the two columns are one **2-column grid**, so each factor slot
shares a row across AM and PM — rows stay level even when a label wraps to 2–3 lines.
Because both columns use the **one day-level order** (see "snowiest wins" above), the
same factor is always in the same row on both sides; where a non-snowing half lacks a
snow figure, that cell is **filled** (`0cm = no new snow` / `–`), not left blank.

**Card sizing:** cards are **wide** (≈350px) and short by default — fine if only ~3 fit
without horizontal scroll, since users typically look at 1–2 days. Width is deliberate:
it keeps the full weather descriptors (e.g. "windy, some lifts may be on hold") on the
card without truncation. Expanding a card grows **that card** taller (it sizes to its own
content, not the row's tallest).

**Date picker:** a clear pill button (`📅 Thu 13 – Mon 17 Aug ▾`), not passive text —
it must read as pressable.

## Preferences

Two ways in, same modal: the **"🎯 What ski factors matter to you?"** button (top-right
of the Overview top bar, a filled blue gradient pill — the one strong accent), **and**
it **auto-opens the first time the user switches to the Resort Recommendation tab** (there's
nothing to show there until prefs exist). Once answered it does not auto-fire again.

**Wizard — one question at a time** (see `mockups/recommendation.html`):
- **One question per screen**, with progress dots + a Back / Next nav. **Next is disabled
  until an option is picked** — every question must be answered, but **"don't mind" is
  always a valid answer**.
- Question set from ARCHITECTURE.md → "User inputs & weighting": ability, cost, bigger
  resort, longer runs, snowy/bluebird. **Branches for beginners** — a beginner is asked
  **only ability + cost**; the advanced questions (size / runs / snow pref) drop out of
  the path (and the dots shorten). Changing the ability answer re-derives the path.
- Options render as big tappable buttons; the selected one highlights.
- On finish → `POST /recommend`, populate the Recommendation view, close the modal.

## Recommendation view

Mockup: **[`mockups/recommendation.html`](mockups/recommendation.html)** — fake data shaped
like `POST /recommend` (each card carries `facts` in the overview's band words, a runner-up
`contrast`, a `day_score`, and the Bedrock `why` paragraph).

- **"Your picks" bar at the top.** Once prefs are submitted the entry button is gone; the
  selections sit in a persistent card as chips (e.g. `Advanced skier · 🗺️ bigger resort`)
  with an **✎ Edit** button that reopens the wizard **pre-filled** — change anything and
  `POST /recommend` re-runs, cards update. Plug-and-play "what matters" tweaking.
- **Section heading:** *"Best resort for each of your selected days, ordered by score."*
- **Result cards** — best resort per day, ranked best-first, capped at 3 (one card per day).
  Each card:
  - **Collapsed** = **rank badge** + **resort** + **day** + **top-3 factor chips**. The chips
    are the card's **highest-priority factors** (the `facts` come back weight-ordered, so they
    reflect what mattered most — including the user's own picks). The **#1 card is styled as
    the "Top pick"** (gold) and **expanded by default**; the rest start collapsed.
  - A **score** shows per card: `day_score` as **`NN/100`** with the caption "our
    ski-conditions model score" — makes the ranking legible/defensible.
  - **Expanded** = the **`why` paragraph** in a highlighted box, **plus the full factor grid**
    (all 8 `facts`, 2-column, same band words + `VALUE = descriptor` style as the Overview).
    Decision: **show both** — the prose persuades, the grid gives the at-a-glance data so the
    user never has to flick back to the Overview. (Answers the "factors again vs just the
    paragraph?" question.)
- **Card copy** mirrors the Overview vocabulary: same-band AM/PM collapse to one row
  (`82, 74% sun = sunny` — AM, PM comma-separated, not slashed); "recent snow"/"new snow" keep the word "snow"; lifts read
  "38 of 45 lifts open". The runner-up `contrast` is currently woven into the prose only
  (no separate visual call-out — may revisit).
- Lives in its own view; flick back to Overview any time (state preserved).

_None of the mockup styling is final — spacing, copy, icons and colours stay open to
tweak when the real frontend is built._

## Data source

Both views are driven by the live backend (see [CLAUDE.md](CLAUDE.md) → Deployment):
- Overview ← `GET /conditions`
- Recommendation ← `POST /recommend`
- Date picker capped at **10 days** out (forecast horizon).

## Visual style & layout (first pass — from the mockup)

The working mockup is **[`mockups/overview.html`](mockups/overview.html)** — a single
self-contained HTML file (no build step; open in a browser) rendering fake data shaped
exactly like `GET /conditions`. It's the reference for coding the real React Overview.
Everything below is a **first pass, open to iteration** — but it's what the mockup shows.

**Top bar (left → right):**
- **Brand** top-left: large "❄ Snowbound" (~46px, bold) with the tagline underneath.
- **View tabs** next to it (pill toggle): "Conditions Overview" / "Resort Recommendation";
  Recommendation is disabled until preferences are set.
- **Spacer**, then the **prefs button** top-right (see Preferences).
- Below the bar: a **date-picker pill** (`📅 Thu 13 – Mon 17 Aug ▾`) — reads as pressable,
  not passive text. Caps at 10 days out.

**Palette / type:** white/blue. Soft blue→white page gradient, white cards, blue accents
(`#2563eb`), amber only for sun. System font stack. Rounded cards (~14px) with soft shadow.

**Resort section:** name + a single meta line of chips —
`84% lifts (38 of 45 open) · 96cm base · elevation 1605–2042 m · <size> · <run length>`.
Then the horizontal day-card row.

- **Missing scraped data → chip omitted.** Lift and base-depth data are scraped from
  OnTheSnow and can be genuinely absent (e.g. Selwyn's open-lift count). When the API
  returns a null for lifts (`pct: null`) or base depth (`cm: null`), the chip is **left out
  of the meta line entirely** (not shown as `–`, which reads like "zero open"). This matches
  the recommendation view, which already drops N/A factors. The backend N/A's that factor
  from scoring too, so the recommendation never invents or zeroes a value it doesn't have.

**Day-card:** ≈**350px wide** (deliberately fat — keeps long weather descriptors intact;
fine if only ~3 fit before horizontal scroll, since users usually look at 1–2 days).
Structure: date header → `recent_snow` line → **AM/PM 2-column grid** (see Per day-card)
→ a centered **"+ more (N)" / "− less"** toggle that grows the whole card. Cards size to
their own content (a row's cards are **not** force-matched in height); expanding one grows
just that card.

**Icons: Lucide (`lucide-react`), coloured semantically.** The emoji placeholders were
swapped for Lucide SVG icons — consistent across OS/browser (emoji render differently on
Windows vs Mac) and cleaner. Defined once in `src/lib/iconMap.js` (`ICONS` name → [component,
colour] + the `sunIconName`/`tempColor`/`factorIconName` helpers), rendered by
`src/lib/Icon.jsx`. Colours are semantic and reuse the card's weather language: snow icons
blue, mix purple, rain slate, sun amber, cloudy grey, wind teal, precip sky-blue; logistics
factors get distinct hues (lifts green, base indigo, ability gold, size teal, runs violet,
price green). **Temperature is colour-banded** to reinforce the reading — cold blue (<0°C),
pleasant green (0–2°C), warm amber (3–6°C), hot red (>6°C).

## Open decisions

Most design decisions are now **made** (day-card factor order, split-day fills, wizard
flow, card layout, copy conventions, palette — all above). What's still genuinely open:

- ~~**Real icon set**~~ — **done:** Lucide, coloured semantically (see "Icons" above). The
  mockups still show emoji, but the built app uses Lucide.
- **Final visual polish** — exact typography scale, spacing, density; to be tuned against
  the mockups while building the real React app (nothing here is locked).
- **Runner-up contrast** — currently only woven into the recommendation `why` prose; may
  or may not get a separate visual call-out on the card. Revisit during build.

Settled (for the record): app name/tagline, tab names, prefs entry button copy + the
auto-open-on-tab behaviour, white/blue palette, card sizing, `VALUE = descriptor` copy.
