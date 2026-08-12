# Architecture

> Living source-of-truth for how the app works. Present tense — updated as
> decisions are made.
>
> Companion docs: [FACTORS.md](FACTORS.md) (per-factor detail and scoring),
> [RESORT_DATA.md](RESORT_DATA.md) (static resort data), and
> [CLAUDE.md](CLAUDE.md) (briefing).

## Overview

A Sydney-focused ski-weekend planner for the three NSW resorts (Perisher,
Thredbo, Selwyn). The user gives a range of days; the app shows a
neutral per-resort conditions overview, asks what matters to them, then returns a
ranked **best resort + day** recommendation with a plain-language explanation. It
is a decision-support tool, not a weather dashboard.

## App flow (user journey)

1. **Pick days** — the user selects a date range they might ski.
2. **Overview** — a neutral, preference-independent per-resort / per-day view of
   conditions. Ordered: **weather → lifts → resort character → cost.**
3. **Pick preferences** — ability + the few things that matter most to them.
4. **Recommendation** — the **best resort for each of the top days** (one card per
   day, ranked best-day-first, capped at 3) as **expandable cards**: a collapsed
   summary (rank, resort, day, headline), expandable to the full "why."

Layout: the **overview** and the **recommendation** are two in-app views the user
flicks between (so opening the recommendation doesn't lose the overview), with
preferences entered via a button/modal in between. See
[FRONTEND_DESIGN.md](FRONTEND_DESIGN.md) for the full visual/layout design.

Key implication: the **overview (step 2) is preference-independent**; the
**scoring/weighting only happens at step 4** once preferences are known. Condition
data is fetched/derived first; preferences are applied on top.

## Architecture (serverless AWS)

Serverless throughout — chosen to showcase cloud skills while staying simple for
a short build.

```
Browser (React app)
   │
   ▼
S3 + CloudFront ......... hosts the static frontend
   │  (API calls)
   ▼
API Gateway → Lambda .... backend: runs scoring model, returns JSON
   │
   ▼
DynamoDB ................ latest fetched conditions per resort

EventBridge (schedule) → Lambda ... periodic fetch of conditions → DynamoDB
```

**Key design choice — split ingest from serving.** A scheduled Lambda
(EventBridge) fetches and caches conditions in DynamoDB; the request-path Lambda
reads from the cache and stays fast. Avoids hammering the data sources on every
page load, and is a clean design story for interviews.

## Data flow

1. **Scheduled ingest** (EventBridge → Lambda, on a timer): fetch weather
   (Open-Meteo) + live lifts/base depth (OnTheSnow) for all three resorts, derive
   the per-window factor values, write to DynamoDB.
2. **Cache** (DynamoDB): holds the latest conditions per resort.
3. **Request** (API Gateway → Lambda): on user request, read cached conditions,
   run the scoring model with the user's preferences, return ranked results +
   explanation as JSON.
4. **Frontend** (React on S3/CloudFront): renders the overview and the
   recommendation.

## Data sources

- **Open-Meteo** (weather) — free, no API key. Provides snowfall, temperature,
  wind (incl. higher levels), freezing level, cloud cover, precipitation, by
  lat/long, with an `elevation` override for downscaling. Validated live: has all
  needed fields, and the three resorts diverge in decision-relevant ways.
- **OnTheSnow** (live, scraped) — open-lift % and reported base depth for all
  three resorts, one consistent page format. Fragile but accepted for a
  short-lived app.

**Caveats worth knowing:**
- **BOM outage / model fallback.** The high-res Australian model (BOM ACCESS) is
  currently suspended, so Open-Meteo falls back to global models (ECMWF/ICON/GFS).
  Data still flows; resolution is just coarser until BOM resumes.

## Forecast horizon

**10 days.** The ingest fetches 10 days of forecast data; the date picker is
capped at 10 days out.

- Open-Meteo's free tier supports up to 16 days, so 10 is within range.
- Forecast accuracy degrades meaningfully beyond ~7 days, but 10 gives people
  enough runway to plan a weekend trip the week before — the main use case.
- We don't show data beyond 10 days rather than showing unreliable figures
  with a disclaimer; the cutoff is a hard cap, not a warning.

## Tech stack & why

- **Frontend: React + Vite** — most interview-relevant frontend skill; Vite's
  static build drops straight into S3/CloudFront.
- **Backend: Python (Lambda)** — plays to existing strengths; ideal for the
  fetch + scoring logic.
- **IaC: AWS SAM** — purpose-built for this serverless shape; fastest path for a
  short build. (Would pick Terraform for multi-cloud / mixed-infra.)
- **Data store: DynamoDB** — simple key-value cache of latest conditions.
- **Explanation text: grounded LLM generation via Amazon Bedrock (Claude Haiku
  4.5)** — the deterministic scorer selects and describes the facts (8 factors +
  contrast, in the overview's band words); Bedrock only **rephrases those exact
  facts into flowing prose**, strictly prompted to add/change/invent nothing. This
  keeps the "why" **faithful** to the computed scores (the guardrail is that every
  fact is pre-computed) while reading naturally, and showcases another AWS service.
  Haiku is right-sized: the task is constrained rephrasing, not reasoning. Falls
  back to a templated join of the facts if Bedrock is unavailable, so `/recommend`
  never fails. (Earlier plan was pure templates, no LLM — revised for readability.)

## Scoring model

Transparent weighted-scoring: each factor → a 0–1 desirability score, weighted by
the user's preferences, combined into one score per (resort, day), then ranked.
Per-factor scores and bands live in [FACTORS.md](FACTORS.md).

### User inputs & weighting

Each factor's **weight** comes from one of three sources:
- **Fixed** — set by us, same for everyone (the objective conditions).
- **User** — only counts if the user opts in; otherwise weight 0.
- **Mix** — a baseline always counts, boosted if the user picks a side.

The user answers a short question set; the answers set the weights:

| Question | Options | Controls | Source |
|---|---|---|---|
| What level skier are you? | beginner / intermediate / advanced | ability-match score per resort (+ Selwyn rule below) | user |
| Is lift ticket cost important? | yes / no | price | user |
| Bigger resort, more terrain? | yes / don't mind | size | user |
| Do you like longer runs? | yes / don't mind | run length | user |
| Snowy/fresh snow, bluebird, or don't mind? | pick one / don't mind | snowy → boost snow amount + recent snow; bluebird → boost sunniness; don't mind → baseline | mix |

- **Beginners are asked nothing further except cost** — they won't have formed
  terrain/snow preferences yet.
- **Hard rule: Selwyn is removed entirely for intermediate/advanced skiers**
  (hard-coded — Selwyn is beginner-only terrain). Beginners keep Selwyn as a
  candidate; it wins naturally for budget beginners (cheapest + most beginner
  terrain), no special-casing needed.
- **Fixed bucket** (always on, weights we set, not asked about): rain penalty,
  snow quality, wind, lifts, base depth. Snow amount / recent snow / sunniness
  carry a fixed **baseline** that the snow-vs-bluebird question can **boost**.

**Weights (out of 10):**

| Factor | Weight | Applies |
|---|---|---|
| Rain penalty (rain/snow) | 10 | always |
| Wind | 8 | always |
| Lifts (open %) | 7 | always |
| Ability match | 6 | always |
| Base depth | 6 | always |
| Snow quality | 5 | when snowing |
| Snow amount | 7 baseline → **9** if "snowy" | when snowing |
| Recent snow | 7 baseline → **10** if "snowy" | always |
| Sunniness | 7 baseline → **10** if "bluebird"; **N/A when snowing** | see below |
| Price | 8 | only if cost matters |
| Size | 6 | only if "bigger resort" |
| Run length | 7 | only if "longer runs" |

**Sunniness-when-snowing rule (Charlotte's refinement):** when it's snowing it's
cloudy anyway, so a powder day shouldn't be marked down for lack of sun. Sunniness
is therefore **N/A when snowing** (drops out of the weighting, for everyone). The
bluebird preference still steers correctly because it works by *rewarding* sunny
days (a clear day gets the big sun contribution a snow day lacks), not by punishing
snow days — so dropping sun on snow days doesn't weaken it.

### Gates (hard vetoes)

Before scoring, a candidate is dropped entirely if:
- **Skier is intermediate/advanced → Selwyn is excluded** (beginner-only terrain).
- **A resort has 0% lifts open** → unskiable, so it's removed across all its days
  (a current-snapshot veto).

Rain is **not** a gate — a rain day stays in with a heavy soft penalty (people do
still ski in the rain).

### Combining scores

Per (resort, day):
1. For each window (morning, afternoon), compute a **window score** = weighted
   average of that window's *active* factors: `Σ(weight × score) ÷ Σ(weights)`.
   N/A factors drop out; resort-level factors (lifts, base depth, resort
   character, price) are the same in both windows.
2. **Day score = ⅔ × better window + ⅓ × worse window** — leans toward the better
   half-day (a good half-day still makes a great day) without ignoring the worse.
3. Rank all (resort, day) day-scores; show the **top 3**.

**Decisions:**
- **#1 — Ranking unit (done):** score each **(resort, day)**, then for each day
  keep the **best resort**, rank the days, and show the **top 3 days** — one card
  per day (a 2-day range yields 2 cards). Chosen over "top 3 raw (resort, day)
  scores" so cards never repeat a resort and each card is genuinely the best place
  to ski that day. Morning/afternoon is *displayed detail*, not a ranking unit.
- **#2 — Per-factor 0–1 scores (done):** all factors scored, including the
  user-dependent ones — ability (hand-set per level), size, run length, and price
  (normalised across the three resorts). See [FACTORS.md](FACTORS.md).
- **#3 — Preferences → weights (done):** question set, weight sources, the Selwyn
  rule, all weight numbers, and the sunniness-when-snowing rule are defined above.
- **#4 — Combining (done):** weighted average of active factors per window; day
  score = ⅔ better window + ⅓ worse window; resort-level factors enter the
  average (differentiate resorts, not days). See "Combining scores" above.
- **#5 — Gates (done):** two hard vetoes — Selwyn for intermediate/advanced
  skiers, and any resort with 0% lifts open. Rain stays soft. See "Gates" above.
- **#6 — Explanation:** each card is an **expandable card** (collapsed summary →
  expand for the full "why"). The why is built from **8 selected factors** — the
  **top 4 by weight** (what matters most / most to the user) plus the **top 4 by
  score** (the most positive conditions), deduped and topped up to 8, with static
  resort factors (size, run length, price) eligible as fillers — each described
  with the **overview band words** (weather factors carry both AM and PM). Plus a
  **2-factor contrast** against the runner-up resort that day, preferring factors
  whose band word actually differs. Selection/description/contrast are all
  deterministic (`scorer.py`); the prose itself is **LLM-generated** — see the
  explanation-text note under *Tech stack & why*. **Contrast is in the first
  build** (promoted from phase-2).

**Conditional logic (snow cluster):** the snow factors are gated by nested checks
(precipitating? → snowing?), and a factor that's N/A drops out of the weighting
rather than scoring 0. Detail in [FACTORS.md](FACTORS.md).
