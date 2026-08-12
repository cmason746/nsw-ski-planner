# CLAUDE.md

> Auto-loaded into context at the start of every session in this directory.
> Keep this lean — it's a briefing. How the app works lives in
> [ARCHITECTURE.md](ARCHITECTURE.md).

## What this project is

A Sydney-focused ski-weekend planning app for NSW ski resorts. It answers one
question: **"Where should I ski this weekend?"**

Rather than just displaying weather data, it compares resorts using live and
forecast conditions, then gives a **clear recommendation of the best resort and
day**, plus a plain-language **explanation of the reasoning**. The user picks
their skiing ability and what matters most to them (e.g. fresh snow, open
terrain, low wind, sunshine), and the app weights its recommendation
accordingly.

## Scope

- **NSW resorts only**, to stay relevant to Sydney-based users.
  Resorts: Perisher, Thredbo, Selwyn.
- **Comparison factors:** snowfall, temperature, freezing level, wind,
  sun/cloud, snow condition/quality, proportion of lifts operating.
- **Output:** ranked recommendation + explanation, not just a data dashboard.

## Tech stack

- **Frontend:** React + Vite (static SPA).
- **Backend:** Python on AWS Lambda.
- **API:** Amazon API Gateway (HTTP API) in front of the Lambda(s).
- **Data store:** Amazon DynamoDB (caches latest conditions per resort).
- **Scheduled ingest:** EventBridge schedule → Lambda, fetches weather on a
  timer and writes to DynamoDB.
- **Hosting:** frontend on S3 + CloudFront.
- **Infrastructure as Code:** AWS SAM.
- **Primary data source:** Open-Meteo (free, no API key) for snowfall, temp,
  wind, freezing level, cloud cover.
- **Live data (scraped from OnTheSnow):** open-lift % and reported base depth for
  all three resorts — a now/tomorrow snapshot, not a forecast (fragility accepted
  given the app's short lifespan). See [FACTORS.md](FACTORS.md).

The full decision-factor spec (all 11 factors, data sources, scoring) lives in
[FACTORS.md](FACTORS.md).

Architecture is serverless throughout. See [ARCHITECTURE.md](ARCHITECTURE.md) for the
reasoning behind each choice.

## Key commands

_TBD — add run / test / build commands here once the stack is set up._

## Architecture & conventions

_TBD — add directory layout and the location of the scoring/recommendation
engine here once it exists._

## TODO (running list — update each session)

- [x] Naming cleanup in `scorer.py`: renamed `resort` → `resort_static` (vs `resort_data` for cached conditions)
- [x] Draw function connection diagrams for each backend file — see [BACKEND_DESIGN.md](BACKEND_DESIGN.md)
- [x] Write `api/handler.py` — routing (GET /conditions, POST /recommend) + `_load_conditions()`; finalise function signatures / variable names first
- [x] Recommendation ranking → **best resort per day** (one card per day, top 3 days), replacing top-3 (resort,day) combos. `scorer.py` now builds an 8-factor "why" package (top-4 by weight + top-4 by score, static factors eligible) + a 2-factor runner-up contrast (prefers band-differing factors), all described with the overview band words.
- [x] Step 2 — `api/explain.py` `generate_why()`: one Bedrock call (Claude Haiku 4.5, `anthropic.claude-haiku-4-5` via `AnthropicBedrockMantle`) rephrases each card's facts into a small paragraph, strictly guardrailed; templated fallback; wired into `POST /recommend`. **Live Bedrock call still untested — needs model access + region at deploy.**
- [x] Implement `format_overview()` in `api/overview.py` — raw cached values → band words + raw numbers (frontend picks icons + lays out as aligned dot points). Precip gate/rain-snow split moved to `shared/factors.py` (`is_precipitating`, `precip_type`) so overview and scorer classify identically.
- [x] Implement `extract_windows()` in `open_meteo.py`
- [x] Implement OnTheSnow scraper (`onthesnow.py`) — parses the `__NEXT_DATA__` JSON blob (Next.js), not the rendered HTML; no bs4 needed
- [ ] Write `template.yaml` (SAM — all AWS infrastructure)
- [ ] Write `samconfig.toml`
- [ ] Deploy SAM skeleton to AWS early (before frontend)
- [ ] Build frontend

## Goals & constraints

- **Hosted on AWS** — a deliberate goal, to demonstrate cloud-computing skills.
  Architecture choices should favour showcasing AWS well.
- **Interview-ready** — Charlotte wants to understand *everything* we build well
  enough to explain it in interviews. Prefer clear, well-understood approaches
  over clever ones; explain the "why" as we go.
- **~2-week timeline** — keep scope simple, but execute it well.
- **First end-to-end app** — frontend especially is new. Claude leads on
  **technical** decisions (architecture, code, tooling, data mechanics),
  suggests next steps, and explains concepts.
- **Division of labour:** Charlotte leads on all **ski / conditions / domain**
  decisions (what factors matter, how to interpret conditions, what makes good
  skiing). Claude does NOT propose its own ski judgment — it surfaces what the
  data can do and implements Charlotte's domain calls. Ask, don't assume, on
  anything ski-related.
- Clean public APIs for Australian resort data (lift status, snow quality) are
  limited; some data may need to come from scraping resort sites. Treat these
  sources as fragile and rate-limit-sensitive.
- Weather/forecast data (snowfall, temp, wind, freezing level) is more tractable
  via open APIs. **Open-Meteo confirmed working** for all needed fields, no key.

## Resort coordinates

Elevations are **lift-served** (lowest / highest lifted point), confirmed by
Charlotte — used for the freezing-level rain/snow split.

| Resort | Lat | Lon | Lowest lifted | Highest lifted |
|---|---|---|---|---|
| Perisher | -36.4058 | 148.4085 | 1605 m | 2042 m |
| Thredbo | -36.5047 | 148.3056 | 1365 m | 2037 m |
| Selwyn | -35.9083 | 148.4500 | 1492 m | 1614 m |
