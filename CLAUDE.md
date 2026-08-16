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

## Git conventions

- **Never add a `Co-Authored-By: Claude ...` trailer or any AI/Claude attribution to
  commit messages.** Write plain commit messages only. This is a hard rule — do not add
  it even if default tooling guidance suggests otherwise.

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
- [x] Step 2 — `api/explain.py` `generate_why()`: one Bedrock call (Claude Haiku 4.5, model id `anthropic.claude-haiku-4-5-20251001-v1:0`) via **boto3 `bedrock-runtime`** (not the Anthropic SDK — so the API Lambda has zero pip deps and needs no Docker to build) rephrases each card's facts into a small paragraph, strictly guardrailed; templated fallback; wired into `POST /recommend`. **Live Bedrock call still untested.**
- [x] Implement `format_overview()` in `api/overview.py` — raw cached values → band words + raw numbers (frontend picks icons + lays out as aligned dot points). Precip gate/rain-snow split moved to `shared/factors.py` (`is_precipitating`, `precip_type`) so overview and scorer classify identically.
- [x] Implement `extract_windows()` in `open_meteo.py`
- [x] Implement OnTheSnow scraper (`onthesnow.py`) — parses the `__NEXT_DATA__` JSON blob (Next.js), not the rendered HTML; no bs4 needed
- [x] Write `template.yaml` (SAM — DynamoDB, shared layer, 2 Lambdas, HTTP API, EventBridge schedule) + `samconfig.toml`
- [x] Deploy SAM skeleton to AWS — **stack is live in ap-southeast-2** (see "Deployment" below)
- [x] Drop the only third-party dep: `ingest` now uses stdlib `urllib` instead of `requests`, so the **whole backend has zero pip deps** (stdlib + runtime boto3) — no Docker/container needed to build
- [x] **Test the deployed backend end-to-end** — fixed float→Decimal bug in ingest, fixed Bedrock inference profile (`au.anthropic.claude-haiku-4-5-20251001-v1:0`). Both endpoints live and returning real data + real Haiku prose.
- [x] Commit backend to git — all of `backend/`, `template.yaml`, `samconfig.toml` pushed.
- [x] Agree frontend design (flow already in ARCHITECTURE.md; visual layer now in [FRONTEND_DESIGN.md](FRONTEND_DESIGN.md))

### Frontend (React + Vite — full app built in `frontend/`)

_Design phase (do first, no real app code yet):_
- [x] **Day-card headline decided** — `recent_snow` on its own top line; `rain_snow` at top of each AM/PM column; top-2 factors + rest expandable; **one factor order per day** ("snowiest wins": snow>mix>rain>dry), both columns share it; split-day snow gaps filled as "no new snow". Full spec in FRONTEND_DESIGN.md.
- [x] Built throwaway **Overview mockup** — `mockups/overview.html` (self-contained, fake data shaped like `GET /conditions`). Agreed: Snowbound brand + tagline, white/blue palette, wide ~350px cards, AM/PM 2-col grid, `VALUE = descriptor` rows, elevation range in resort header, date-picker pill.
- [x] Mock up the **Recommendation view** + the **preferences wizard** — `mockups/recommendation.html`. Agreed: one-question-at-a-time modal (auto-opens on entering the tab; every Q required, "don't mind" valid; beginners only asked ability+cost), persistent "Your picks" bar + ✎ Edit, ranked cards (rank + resort + day + top-3 weight-ordered factor chips + `NN/100` model score), expand → `why` prose **plus** full 8-factor grid.
- [x] **Visual style** — white/blue palette + card layout from the mockups; **icon set → Lucide** (coloured semantically; temperature colour-banded). Typography/spacing tuned live against the mockups. See FRONTEND_DESIGN.md → "Icons" / "Visual style".

_Build phase (the mockups in `mockups/` are the visual reference — build is mostly mockup → React translation). Do roughly in order:_
- [x] **Plan the component breakdown + folder structure** — agreed: CSS Modules, all shared state in `App.jsx` (props down, no Redux/router), both views stay mounted (`hidden`) so tab switches keep state. Full tree + build order in [FRONTEND_DESIGN.md](FRONTEND_DESIGN.md) → "Component architecture".
- [x] **Check CORS on the HTTP API** — already configured (`CorsConfiguration`: origins `*`, methods GET/POST, all headers) **and verified live**: preflight `OPTIONS /recommend` → 204 with the right `access-control-*` headers; `GET /conditions` returns `access-control-allow-origin: *`. Gateway handles preflight + injects headers, so the Lambda adds none. _Later: tighten `AllowOrigins` to the CloudFront domain once hosted (comment already in `template.yaml`)._
- [x] **App shell** — `App.jsx` (shared state) + `TopBar` (brand, tab pill, prefs button) + `tokens.css` + placeholder Overview/Recommendation views. Tab switch preserves state; Recommendation tab disabled until prefs set. `npm install` done; `npm run build` + `npm run lint` clean. Prefs button is a temporary stub (sets placeholder prefs to unlock the tab) until the wizard lands.
- [x] **Overview view** wired to `GET /conditions` — three resort sections, AM/PM day-cards, date-range filter, expand. `overview/` (OverviewView → ResortSection → DayCard → FactorCell) + `lib/overviewFormat.js` + `api/client.js`.
- [x] **Preferences wizard + Recommendation view** wired to `POST /recommend` — one-question-at-a-time modal (incl. a **date-range step**, pre-filled from the overview selection), "Your picks" bar + ✎ Edit, ranked result cards with real Haiku "why" prose. `recommend/` (RecommendationView, PreferencesWizard, PrefBar, ResultCard) + `lib/recommendFormat.js`.
- [x] **Date picker** (≤10 days out) — shared `components/DatePicker.jsx` (contiguous-range calendar), used by both the Overview pill and the wizard step; single shared `dateRange` in `App.jsx`; default = today + next 6 days.
- [x] **Icon pass** — Lucide (`lucide-react`), coloured semantically, temperature colour-banded. One swap-point: `lib/iconMap.js` + `lib/Icon.jsx`.
- [x] **Commit the frontend to git** — done (commit `7e380a5`, pushed). `frontend/` is now tracked; `node_modules`/`dist` gitignored via Vite's `.gitignore`.
- [ ] **Discuss AWS hosting options** (before building the hosting) — S3 static hosting vs S3 + CloudFront, custom domain / address name (Route 53, ACM cert), and how it all fits together. Talk through the options + trade-offs first, then decide.
- [ ] **Build + host** on S3 + CloudFront.
- [ ] **Tighten CORS for prod** — narrow `AllowOrigins` in `template.yaml` from `*` to the CloudFront (and any custom-domain) origin once hosting is set up. Comment already flags the spot.

_State (as of 2026-08-16):_
- Frontend **built and working end-to-end** against the live API — Overview + Recommendation + preferences wizard + date picker + Lucide icons. `npm run build`/`npm run lint` clean; runs via `npm run dev` (Vite, http://localhost:5173).
- Backend serves everything needed and the Bedrock "why" prose is **live** (account subscribed to Claude Haiku 4.5 on Bedrock — required a valid payment instrument, now sorted).
- **Frontend committed + pushed** (commit `7e380a5`); backend committed + deployed.
- **All that's left is hosting:** discuss + build S3/CloudFront hosting, then tighten CORS (`AllowOrigins` `*` → the CloudFront/custom-domain origin). Nothing else outstanding.

## Deployment

Live serverless backend, deployed with AWS SAM.

- **Region:** `ap-southeast-2` (Sydney) — everything, incl. the Bedrock call (Haiku 4.5 is available there).
- **Stack:** `nsw-ski-planner` · **AWS CLI profile:** `ski-planner` (personal account) · **region:** `ap-southeast-2`.
- **API base URL:** `https://ayyfk7jzlb.execute-api.ap-southeast-2.amazonaws.com` → `GET /conditions`, `POST /recommend`.
- **DynamoDB table:** `nsw-ski-planner-ConditionsTable-8ER2M7M89UK3`.
- **Build/deploy:** from repo root, `sam build` then `sam deploy` (no `--use-container`; needs local `python3.12`, installed via brew). `samconfig.toml` pins profile/region/model-id.
  - **Always deploy non-interactively.** `samconfig.toml` sets `confirm_changeset = false`; if ever deploying by hand or from a fresh config, pass **`--no-confirm-changeset`** — otherwise `sam deploy` prints the changeset and **hangs waiting for a y/N** that can't be answered here.
- **Cost:** effectively free — Lambda/DynamoDB/EventBridge/HTTP API all free-tier; only Bedrock tokens cost (cents).

## Next — testing the deployed backend

1. **Populate the cache:** invoke the ingest Lambda by hand (schedule is every 3h; until it runs, `GET /conditions` returns 503).
2. **`GET /conditions`** → overview JSON.
3. **`POST /recommend`** (body keys: `ability, cost_matters, bigger_resort, longer_runs, snow_pref, selected_dates`) → ranked cards + Haiku "why" prose from Bedrock.
4. Then → **frontend**.

Turnkey commands (profile `ski-planner`, region `ap-southeast-2`):

```bash
# 1. Invoke ingest to populate DynamoDB (prints tailed logs base64 → decode)
FN=$(aws cloudformation describe-stack-resource --stack-name nsw-ski-planner \
  --logical-resource-id IngestFunction --query 'StackResourceDetail.PhysicalResourceId' \
  --output text --profile ski-planner --region ap-southeast-2)
aws lambda invoke --function-name "$FN" --log-type Tail \
  --profile ski-planner --region ap-southeast-2 /tmp/ingest.json

# 2. Overview
curl -s https://ayyfk7jzlb.execute-api.ap-southeast-2.amazonaws.com/conditions | python3 -m json.tool

# 3. Recommendation — set selected_dates to dates seen in the overview
curl -s -X POST https://ayyfk7jzlb.execute-api.ap-southeast-2.amazonaws.com/recommend \
  -H 'Content-Type: application/json' \
  -d '{"ability":"beginner","cost_matters":false,"snow_pref":"snowy","selected_dates":["YYYY-MM-DD","YYYY-MM-DD"]}' \
  | python3 -m json.tool

# CloudWatch logs for a function (swap IngestFunction / ApiFunction)
sam logs --stack-name nsw-ski-planner --name IngestFunction --profile ski-planner --region ap-southeast-2
```

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
