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

**Status: fully built and deployed end-to-end on AWS.** Backend + frontend are
live; the only remaining spend is Bedrock tokens (cents). Live site:
**http://nsw-snowbound.s3-website-ap-southeast-2.amazonaws.com**

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
- **Hosting:** frontend on **plain S3 static website hosting** — bucket
  `nsw-snowbound`, public-read, HTTP only. We deliberately chose plain S3 over
  S3 + CloudFront: both are free at this scale, but for a personal project the
  latency (CDN) and HTTPS benefits were judged overkill, and a public-read
  bucket is an acceptable risk with no logins / no sensitive data. CloudFront
  remains the "proper" production pattern if the app ever needs HTTPS, a custom
  domain, or edge caching.
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

**Frontend (from `frontend/`):**

```bash
npm run dev      # local dev server — http://localhost:5173
npm run build    # production build → frontend/dist/
npm run lint     # oxlint
```

**Backend / infra (from repo root):** see "Deployment" below.

## Architecture & conventions

- **Backend** (`backend/`): two Lambdas sharing a layer.
  - `shared/` — resort data (`resorts.py`) + factor classification/scoring
    (`factors.py`, `scorer.py`); packaged as a SAM layer, reused by both Lambdas.
  - `ingest/` — scheduled fetch (Open-Meteo via stdlib `urllib`, OnTheSnow via the
    `__NEXT_DATA__` JSON blob) → writes the cache to DynamoDB.
  - `api/` — `handler.py` routes `GET /conditions` (overview) and
    `POST /recommend` (ranked cards); `overview.py` formats cached values into
    band words + raw numbers; `explain.py` calls Bedrock (Haiku 4.5) for the
    "why" prose with a templated fallback.
  - **Zero pip deps** — stdlib + runtime boto3 only, so no Docker/container is
    needed to build.
- **Frontend** (`frontend/src/`): CSS Modules; all shared state lives in
  `App.jsx` (props down, no Redux/router); both views stay mounted (`hidden`) so
  tab switches preserve state. Layout: `overview/` + `recommend/` view trees,
  shared `components/`, formatting in `lib/`, API calls in `api/client.js`.
  Icons via Lucide (`lib/iconMap.js` + `lib/Icon.jsx`). Full component tree and
  the visual spec are in [FRONTEND_DESIGN.md](FRONTEND_DESIGN.md).

## TODO (running list — update each session)

The app is complete and deployed. Nothing outstanding. Historical build items
are in git history; the frontend build breakdown lives in
[FRONTEND_DESIGN.md](FRONTEND_DESIGN.md).

Possible future enhancements (none planned):

- [ ] Move to S3 + CloudFront if HTTPS / a custom domain / edge caching is ever
      wanted (a custom domain would cost ~$12/yr to register — deliberately
      skipped for now).
- [ ] Automate the frontend deploy (build → `s3 sync`) rather than running it by
      hand.

_State (as of 2026-08-16):_
- **Whole app live on AWS.** Backend (Lambdas, DynamoDB, HTTP API, EventBridge
  ingest, Bedrock "why" prose) deployed; frontend built and hosted on the
  `nsw-snowbound` S3 website bucket, serving the SPA over HTTP.
- Overview + Recommendation + preferences wizard + date picker + Lucide icons
  all working end-to-end against the live API. Bedrock Haiku 4.5 prose is live.
- CORS on the HTTP API is **locked to the S3 website origin**
  (`AllowOrigins: !GetAtt SiteBucket.WebsiteURL`), no longer `*`.
- Frontend committed + pushed (commit `7e380a5`); the S3 hosting resources in
  `template.yaml` are the latest uncommitted change (commit when ready).

## Deployment

Live serverless app, deployed with AWS SAM.

- **Region:** `ap-southeast-2` (Sydney) — everything, incl. the Bedrock call (Haiku 4.5 is available there).
- **Stack:** `nsw-ski-planner` · **AWS CLI profile:** `ski-planner` (personal account) · **region:** `ap-southeast-2`.
- **Live site:** `http://nsw-snowbound.s3-website-ap-southeast-2.amazonaws.com` (plain S3 website hosting).
- **API base URL:** `https://ayyfk7jzlb.execute-api.ap-southeast-2.amazonaws.com` → `GET /conditions`, `POST /recommend`.
- **DynamoDB table:** `nsw-ski-planner-ConditionsTable-8ER2M7M89UK3`.
- **S3 site bucket:** `nsw-snowbound`.

### Deploy the backend / infra

From repo root, `sam build` then `sam deploy` (no `--use-container`; needs local
`python3.12`, installed via brew). `samconfig.toml` pins profile/region/model-id.

- **Always deploy non-interactively.** `samconfig.toml` sets
  `confirm_changeset = false`; if ever deploying by hand or from a fresh config,
  pass **`--no-confirm-changeset`** — otherwise `sam deploy` prints the changeset
  and **hangs waiting for a y/N** that can't be answered here.

### Deploy the frontend

SAM only provisions the bucket — the built site files are uploaded out-of-band.
After any frontend change:

```bash
# 1. Build the SPA
cd frontend && npm run build && cd ..

# 2. (only if template.yaml changed) update the infra
sam build && sam deploy

# 3. Upload the build to the site bucket
aws s3 sync frontend/dist s3://nsw-snowbound --delete \
  --profile ski-planner --region ap-southeast-2
```

Then the new build is live at the site URL immediately (no CDN cache to
invalidate — that's a plain-S3 upside).

- **Cost:** effectively free — Lambda/DynamoDB/EventBridge/HTTP API/S3 all
  free-tier; only Bedrock tokens cost (cents).

### Testing the deployed backend directly

Turnkey commands (profile `ski-planner`, region `ap-southeast-2`):

```bash
# Invoke ingest by hand to populate DynamoDB (schedule runs every 3h; until it
# has run, GET /conditions returns 503)
FN=$(aws cloudformation describe-stack-resource --stack-name nsw-ski-planner \
  --logical-resource-id IngestFunction --query 'StackResourceDetail.PhysicalResourceId' \
  --output text --profile ski-planner --region ap-southeast-2)
aws lambda invoke --function-name "$FN" --log-type Tail \
  --profile ski-planner --region ap-southeast-2 /tmp/ingest.json

# Overview
curl -s https://ayyfk7jzlb.execute-api.ap-southeast-2.amazonaws.com/conditions | python3 -m json.tool

# Recommendation — set selected_dates to dates seen in the overview
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
