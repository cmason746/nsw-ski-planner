# Snowbound 🏔️

**A decision-support app that tells you where to ski this weekend — and explains why.**

> Your guide to NSW's ski resorts. Live conditions in, a ranked recommendation out.

🔗 **Live demo:** http://nsw-snowbound.s3-website-ap-southeast-2.amazonaws.com

---

## A look at it

| Conditions Overview | Resort Recommendation |
|---|---|
| ![The Conditions Overview — a neutral, per-resort view of live and forecast conditions across the selected days.](screenshots/overview.png) | ![The Resort Recommendation — ranked best-resort-per-day cards, expanded to show the plain-language "why".](screenshots/recommendation.png) |
| *Neutral, per-resort conditions for the days you picked.* | *Ranked recommendation with an expandable, LLM-generated explanation.* |

---

## The problem

Planning a ski weekend from Sydney means checking the same three NSW resorts
(Perisher, Thredbo, Selwyn) across a handful of weather sites, mentally juggling
snowfall, wind, freezing levels, lift closures and ticket prices — and then
guessing. Every weather app shows you *data*; none of them answer the actual
question: **"where should I go, and which day?"**

Snowbound answers that question. You pick the days you *could* ski and what
matters to you (ability, fresh snow vs. bluebird sun, cost, terrain), and it
returns a **ranked recommendation of the best resort per day** with a
**plain-language explanation of the reasoning** — not a dashboard you still have
to interpret.

## What it does

1. **Pick your days** — a date range up to 10 days out (the useful forecast horizon).
2. **Conditions Overview** — a neutral, per-resort / per-day view of live and
   forecast conditions. No opinion yet, just the facts, laid out consistently.
3. **Tell it what matters** — a short preferences wizard: ability level, cost
   sensitivity, terrain size, run length, and whether you're chasing powder or sun.
4. **Recommendation** — the best resort for each of your top days, ranked, as
   expandable cards: a one-line headline, expandable to the full "why."

The recommendation is **preference-aware**: the same conditions produce a
different answer for a budget-conscious beginner than for an advanced skier
chasing fresh snow.

## It interprets the conditions, not just displays them

The Overview doesn't just show raw numbers — it tells you what they *mean* for
skiing. Most people don't know what wind speed puts the lifts on hold, or what
temperature makes for good-quality snow. So every figure comes with a
plain-language read alongside it:

- **Wind** — *52 km/h* is labelled *"very windy, lifts likely to be on hold"*,
  not just left as a number.
- **Snow quality** — a temperature of *−4 °C* is called *"dry & light quality
  snow"*; near-freezing gets flagged as wet and sticky.
- **Freezing level** — translated into *"snow across the whole resort"* vs
  *"snow up high, rain below ~1550 m"*.

The raw figure is always there too — the interpretation sits next to it, so a
newer skier gets a straight answer and learns the reasoning as they go.

## Why I built it

I love the snow, and every winter I go through the same ritual: half a dozen
browser tabs across the three resorts, trying to work out where conditions will
actually be best. Nothing pulls it together in one place, and nothing turns the
raw numbers into a straight answer.

I also have friends newer to skiing who always ask me where and when they should
go. Snowbound is the answer I'd give them — it aggregates the data for all three
NSW resorts and turns it into a clear, beginner-friendly recommendation with the
reasoning spelled out.

---

## Architecture

Serverless throughout, on AWS, deployed as infrastructure-as-code.

```
                       ┌────────────────────────────────┐
                       │   Browser — React + Vite SPA   │
                       │ (Conditions ⇄ Recommendation)  │
                       └────────────────┬───────────────┘
     S3 static hosting                  │  HTTPS (JSON)
    ┌───────────────────────────────────┼───────────────────────────────────┐
    │                                   ▼                                   │
    │                      ┌────────────────────────┐                       │
    │                      │ API Gateway (HTTP API) │                       │
    │                      └────────────┬───────────┘                       │
    │                                   ▼                                   │
    │                      ┌────────────────────────┐                       │
    │                      │  API Lambda (Python)   ┤──► Bedrock            │
    │                      │ scoring model + "why"  │    (Haiku 4.5)        │
    │                      └────────────┬───────────┘                       │
    │                                   ▼                                   │
    │                      ┌────────────────────────┐                       │
    │                      │        DynamoDB        │ latest cached         │
    │                      │   (conditions cache)   │ conditions            │
    │                      └────────────────────────┘                       │
    │                                   ▲                                   │
    │                                   │                                   │
    │  EventBridge schedule ────► Ingest Lambda (Python)                    │
    │                             fetches + derives conditions              │
    └───────────────────────────────────┬───────────────────────────────────┘
                                        │
                      ┌─────────────────┴─────────────────┐
                      ▼                                   ▼
              Open-Meteo API                        OnTheSnow
         (snowfall, temp, wind,                 (open-lift %, base depth
          freezing level, cloud)                 — scraped snapshot)
```

**The key design decision: split ingest from serving.** A scheduled Lambda
fetches and caches conditions in DynamoDB on a timer; the request-path Lambda
only ever reads the cache. This keeps user requests fast, avoids hammering (and
getting rate-limited by) the upstream data sources on every page load, and
cleanly decouples "getting data" from "serving answers." It's the same
read-through-cache pattern you'd reach for at scale, sized down to a personal app.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| **Frontend** | React + Vite (static SPA) | Component model + a build that drops straight onto S3. CSS Modules for scoped styling, no framework sprawl. |
| **Backend** | Python on AWS Lambda | Right tool for the fetch + scoring logic; **zero pip dependencies** (stdlib + runtime boto3), so no containers to build. |
| **API** | API Gateway (HTTP API) | Thin, cheap HTTP front door for the Lambdas. |
| **Data store** | DynamoDB | Simple key-value cache of the latest conditions per resort. |
| **Scheduled ingest** | EventBridge → Lambda | Timer-driven fetch, decoupled from the request path. |
| **LLM** | Amazon Bedrock (Claude Haiku 4.5) | Grounded prose generation with a templated fallback. |
| **Hosting** | S3 static website hosting | Plain S3, HTTP-only — see the tradeoff below. |
| **IaC** | AWS SAM | Purpose-built for this serverless shape; whole stack is reproducible from `template.yaml`. |

## Grounded LLM explanations

The explanation prose is generated by **Claude Haiku 4.5 via Amazon Bedrock** —
but with a strict separation of concerns designed to make hallucination
structurally impossible:

- A **deterministic Python scorer** does all the reasoning. It selects which
  facts to mention (the factors that matter most to *this* user plus the most
  favourable conditions), describes each in fixed "band words" (e.g. *"15–20 cm
  fresh snow, morning"*), and computes a contrast against the runner-up resort.
- **Bedrock only rephrases those exact facts into flowing prose** — strictly
  prompted to add nothing, invent nothing, change no numbers. The LLM is a
  *writer*, never a *reasoner*.
- If Bedrock is unavailable, it **falls back to a templated join** of the same
  facts, so `/recommend` never fails.

The result reads naturally but is provably faithful to the computed scores —
every fact in the prose was pre-computed by code. Haiku is deliberately
right-sized: constrained rephrasing doesn't need a frontier model.

## The scoring model

Transparent weighted scoring — no black box. Each of 11 factors maps to a 0–1
desirability score and carries a weight; the user's preferences adjust the
weights; scores are combined per `(resort, day)` and ranked.

- **Factors:** snowfall, rain-vs-snow (via freezing level), snow quality,
  recent snow, base depth, wind, sun/cloud, open-lift %, ability match, resort
  size, run length, and price.
- **Preference-driven weighting:** e.g. picking "chasing powder" boosts fresh
  snow; "bluebird" boosts sun; cost sensitivity switches price on.
- **Domain rules baked in:** Selwyn (beginner-only terrain) is excluded for
  intermediate/advanced skiers; a resort with 0% lifts open is vetoed entirely;
  sun is dropped as a factor on snowing days (a powder day shouldn't be marked
  down for cloud).
- **Day score** leans toward the better half-day (⅔ better window + ⅓ worse) —
  a great morning still makes a great day.

Full factor-by-factor spec, data sources, and scoring curves are in
[FACTORS.md](FACTORS.md); the model and its design decisions are in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Engineering decisions & tradeoffs

A few of the choices worth calling out, and what I traded off:

- **Serverless, not a server.** No instance to patch or scale; the app costs
  effectively nothing at rest (only Bedrock tokens cost anything — cents).
  Tradeoff: cold starts, which are irrelevant for this traffic profile.
- **Plain S3 over S3 + CloudFront.** Both are free here, so I skipped the CDN —
  HTTP-only is fine for a project with no logins or sensitive data. CloudFront is
  the upgrade path if it ever needs HTTPS or a custom domain.
- **Read-through cache.** Upstream data is fetched on a schedule and cached, not
  fetched per request — protects fragile scraped sources and keeps latency low.
- **Scraping accepted as fragile.** Australian resorts have no clean lift-status
  API, so open-lift % and base depth are scraped from OnTheSnow's embedded JSON.
  I treat this as a known-fragile dependency, isolated to the ingest Lambda, for
  a deliberately short-lived app.

---

## Repository layout

```
backend/
  shared/     resort data + factor classification & scoring (packaged as a SAM layer)
  ingest/     scheduled fetch: Open-Meteo (urllib) + OnTheSnow → DynamoDB
  api/        GET /conditions (overview) + POST /recommend (ranked cards + Bedrock "why")
frontend/     React + Vite SPA (CSS Modules; state in App.jsx, props down)
template.yaml AWS SAM — the entire stack as infrastructure-as-code
```

## Running it locally

**Frontend** (from `frontend/`):

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build → frontend/dist/
```

**Backend / infra** (from repo root, needs the AWS SAM CLI + local `python3.12`):

```bash
sam build
sam deploy       # deploys the full serverless stack to ap-southeast-2
```

## Documentation

This repo is documented as if handing it to another engineer:

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the app works, data flow, the
  scoring model, and the reasoning behind each choice.
- **[BACKEND_DESIGN.md](BACKEND_DESIGN.md)** — how the backend code fits
  together: which function calls which, and why.
- **[FACTORS.md](FACTORS.md)** — every decision factor: what it is, why it
  matters, its data source, and how it scores.
- **[FRONTEND_DESIGN.md](FRONTEND_DESIGN.md)** — the frontend component tree and
  visual spec.
- **[RESORT_DATA.md](RESORT_DATA.md)** — the static per-resort data.
