# Backend Design — Function Flow

> Living map of how the backend code fits together. Companion to
> [ARCHITECTURE.md](ARCHITECTURE.md) (system-level design and the scoring model)
> and [FACTORS.md](FACTORS.md) (per-factor detail). This doc is about the **code**:
> which function calls which, and why.

## How to read these diagrams

- **A box** is a deployable unit (a Lambda, DynamoDB, an external API). Inner
  boxes group functions by the **source file** they live in.
- **A node** is one function — its name plus a one-sentence description of what it
  does.
- **An arrow** is a function call (or data read/write); its **label says why** the
  call happens, or when.
- **Colour = build status:**

| Colour | Meaning |
|---|---|
| 🟩 green | implemented |
| 🟧 amber (dashed) | named but not yet implemented, or a stub with a `NotImplementedError` |
| 🟦 blue | external service (HTTP) |
| 🟪 purple | AWS-managed store / trigger |

Dashed **arrows** mark calls that are planned but not wired up yet.

---

## 1. System overview

The two Lambdas never talk to each other — they're decoupled through DynamoDB.
The ingest Lambda **writes** the cache on a timer; the API Lambda **reads** it on
request. This is the "split ingest from serving" decision in
[ARCHITECTURE.md](ARCHITECTURE.md).

```mermaid
flowchart TD
    FE["Frontend (React on S3 / CloudFront) — renders the overview and the recommendation"]:::built
    AGW["API Gateway (HTTP API) — both routes point to the one API Lambda"]:::store
    EB["EventBridge schedule — fires every few hours"]:::store
    API["API Lambda — handles both routes: returns the overview, and scores the recommendation"]:::built
    INGEST["Ingest Lambda — fetches conditions, writes cache"]:::built
    DDB[("DynamoDB — ConditionsTable — one item per resort: forecast windows + live lift/base snapshot")]:::store
    OM["Open-Meteo — hourly weather forecast, no API key"]:::ext
    OTS["OnTheSnow — live lift status and base depth (scraped)"]:::ext

    FE -->|"call 1 — GET /conditions (after picking dates)"| AGW
    FE -->|"call 2 — POST /recommend (after picking preferences)"| AGW
    AGW -->|"invokes; routes on method + path"| API
    API -->|"GET — read cache, return overview"| DDB
    API -->|"POST — read same cache, then score"| DDB
    EB -->|"invokes on a timer"| INGEST
    INGEST -->|"fetch weather forecast"| OM
    INGEST -->|"scrape lifts and base depth"| OTS
    INGEST -->|"put_item, one per resort"| DDB

    classDef built fill:#d3f9d8,stroke:#2b8a3e,color:#000;
    classDef ext fill:#e7f5ff,stroke:#1971c2,color:#000;
    classDef store fill:#f3e8ff,stroke:#7048e8,color:#000;
```

---

## 2. Ingest Lambda

Triggered by EventBridge. `lambda_handler` orchestrates everything: it grabs the
live lift/base snapshot for all resorts once, then loops the resorts fetching and
slicing weather, and writes one item per resort to DynamoDB. The numbered labels
follow the order of execution.

```mermaid
flowchart TD
    EB["EventBridge schedule"]:::store

    subgraph INGEST["Ingest Lambda"]
        subgraph ing_handler["ingest/handler.py"]
            main["lambda_handler(event, context) — entry point; orchestrates the full ingest and writes each resort to DynamoDB"]:::built
        end

        subgraph ing_ots["ingest/onthesnow.py"]
            ots_all["fetch_all_snapshots() — returns a live lift/base snapshot for all three resorts, keyed by resort"]:::built
            ots_one["fetch_resort_snapshot(resort_key) — fetches one resort's OnTheSnow ski-report page and parses lifts_open, lifts_total, base_depth_cm"]:::built
        end

        subgraph ing_meteo["ingest/open_meteo.py"]
            meteo_fetch["fetch_resort_forecast(lat, lon, elevation_high, elevation_mid) — fetches one resort's hourly forecast via two elevation-specific calls and merges them"]:::built
            meteo_low["_fetch(lat, lon, elevation, variables, past_days) — performs a single Open-Meteo HTTP GET and returns the raw JSON"]:::built
            meteo_windows["extract_windows(hourly) — slices raw hourly data into per-day AM/PM windows with aggregated factor values"]:::built
        end

        subgraph ing_shared["shared/resorts.py"]
            resorts_data["RESORTS — static per-resort config: coordinates and low / mid / high elevations"]:::built
        end
    end

    OM["Open-Meteo"]:::ext
    OTS["OnTheSnow"]:::ext
    DDB[("DynamoDB — ConditionsTable")]:::store

    EB -->|"invokes on a timer"| main
    main -->|"step 1 — live lift/base for all resorts, once"| ots_all
    ots_all -->|"once per resort"| ots_one
    ots_one -->|"HTTP GET the ski-report page"| OTS
    main -->|"iterate resorts to fetch"| resorts_data
    main -->|"step 2 — fetch weather per resort"| meteo_fetch
    meteo_fetch -->|"two calls: high-elevation vars, then mid-elevation temp"| meteo_low
    meteo_low -->|"HTTP GET the forecast"| OM
    main -->|"step 3 — slice hourly into AM/PM windows"| meteo_windows
    main -->|"step 4 — put_item, one item per resort"| DDB

    classDef built fill:#d3f9d8,stroke:#2b8a3e,color:#000;
    classDef todo fill:#fff3bf,stroke:#e67700,color:#000,stroke-dasharray: 5 3;
    classDef ext fill:#e7f5ff,stroke:#1971c2,color:#000;
    classDef store fill:#f3e8ff,stroke:#7048e8,color:#000;
```

**Note on `extract_windows`.** It's on the critical path — its output shape is
exactly what the scorer's per-window scoring reads back out of DynamoDB, so it defines the
DynamoDB item schema.

**Note on `fetch_resort_snapshot`.** OnTheSnow is a Next.js app: every ski-report
page server-renders with all its data in one `<script id="__NEXT_DATA__">` JSON
blob. We parse `props.pageProps.fullResort` out of that blob (lift counts +
per-band depths in cm) rather than scraping rendered divs — it's the resort's own
structured data, so no unit conversion and far less fragile than div-scraping.
Base depth is reported per elevation band; we take the first present in base →
middle → summit order.

---

## 3. API Lambda

Triggered by API Gateway. `GET /conditions` just returns the cached overview;
`POST /recommend` loads the cache and runs the scoring model with the user's
preferences. `scorer.rank` is the heart of it — everything below `rank` is the
scoring model from [ARCHITECTURE.md](ARCHITECTURE.md). Arrows are numbered per
route (**GET 1–2**, **POST 1–3**), like the ingest diagram.

```mermaid
flowchart TD
    AGW["API Gateway (HTTP API)"]:::store

    subgraph API["API Lambda"]
        subgraph api_handler["api/handler.py"]
            api_main["lambda_handler(event, context) — entry point; routes GET /conditions and POST /recommend"]:::built
            api_load["_load_conditions() — reads all resort items from DynamoDB into the conditions dict (shared by both routes)"]:::built
        end

        subgraph api_overview["api/overview.py"]
            overview["format_overview(conditions) — turns the raw cached values into the human-readable overview (band labels and words); the frontend picks the icons"]:::built
        end

        subgraph api_scorer["api/scorer.py"]
            rank["rank(conditions, preferences) — scores every (resort, day), keeps the best resort per day, ranks days, returns up to 3 cards — each with an 8-factor why + runner-up contrast"]:::built
            gates["apply_gates(candidates, conditions, preferences) — drops ineligible candidates — Selwyn for intermediate/advanced, and any resort with 0% lifts open"]:::built
            window["_weather_scores · _resort_scores · _window_score · _combined_scores — per-factor 0–1 scores per window (N/A drop out); weighted-average one window; mean across windows for selection"]:::built
            day["score_day(am, pm) — combines the two windows into one day score: two-thirds the better window plus one-third the worse"]:::built
            topf["select_factors · _describe_factor · _build_contrast — picks 8 factors (top-4 weight + top-4 score), describes them in the overview band words, builds the 2-factor runner-up contrast"]:::built
        end

        subgraph api_explain["api/explain.py"]
            explain["generate_why(cards, preferences) — Bedrock (Claude Haiku 4.5) rephrases each card's fact package into prose, guardrailed to the facts; templated fallback if unavailable"]:::built
        end

        subgraph api_factors["shared/factors.py"]
            weights["build_weights(preferences) — turns user preferences into a factor→weight dict (opt-ins plus snowy / bluebird boosts)"]:::built
            isprecip["is_precipitating(precip_mm, precip_prob) — true if precip is likely and meaningful — the gate for the whole snow story"]:::built
            ptype["precip_type(freezing_level_m, elev_low, elev_high) — classifies precipitation as snow, mix, or rain from freezing level vs resort elevations"]:::built
            subgraph FACTORS["scoring functions — each maps a reading to 0–1"]
                f_rain["score_rain_penalty(...) — 1 all-snow, 0.3 mix, 0 all-rain"]:::built
                f_wind["score_wind(...) — 1 at 15 km/h or less, down to 0 at 60 km/h or more"]:::built
                f_amount["score_snow_amount(cm) — min(cm / 20, 1)"]:::built
                f_quality["score_snow_quality(temp_c) — cold → 1, marginal → 0.5, warm → 0"]:::built
                f_recent["score_recent_snow(cm) — min(cm / 40, 1)"]:::built
                f_base["score_base_depth(cm) — clamp((cm − 30) / 60, 0, 1)"]:::built
                f_sun["score_sunniness(cloud_pct) — 1 − cloud_cover / 100"]:::built
                f_lifts["score_lifts(open, total) — open / total"]:::built
            end
        end

        subgraph api_resorts["shared/resorts.py"]
            rscores["ABILITY_SCORES · SIZE_SCORES · LENGTH_SCORES · PRICE_SCORES (0–1 scores) — SIZE_LABELS · LENGTH_LABELS · TERRAIN_LABELS (overview character words) — static per-resort lookup tables"]:::built
        end
    end

    DDB[("DynamoDB — ConditionsTable")]:::store
    BEDROCK["Amazon Bedrock — Claude Haiku 4.5 — rephrases facts into prose"]:::ext

    AGW -->|"invokes on each request"| api_main

    %% GET /conditions — read cache, format, return
    api_main -->|"GET 1 · POST 1 — load the cache"| api_load
    api_load -->|"read all resort items"| DDB
    api_main -->|"GET 2 — format for display"| overview

    %% POST /recommend — load cache, score, generate prose
    api_main -->|"POST 2 — score with prefs"| rank
    api_main -->|"POST 3 — generate the why prose"| explain
    explain -->|"grounded rephrasing (strict prompt)"| BEDROCK

    %% inside rank — the scoring model (zoom-in on POST 2)
    rank -->|"prefs → factor weights"| weights
    rank -->|"drop ineligible (resort, day) combos"| gates
    rank -->|"score each half-day (AM and PM)"| window
    rank -->|"combine the two windows"| day
    rank -->|"select + describe factors, build contrast"| topf
    window -->|"is precip likely and meaningful?"| isprecip
    window -->|"if precipitating, classify the type"| ptype
    window -->|"score each active factor"| FACTORS
    window -->|"look up user-dependent scores"| rscores
    topf -->|"static character labels"| rscores

    classDef built fill:#d3f9d8,stroke:#2b8a3e,color:#000;
    classDef todo fill:#fff3bf,stroke:#e67700,color:#000,stroke-dasharray: 5 3;
    classDef store fill:#f3e8ff,stroke:#7048e8,color:#000;
```

**Notes.**
- The two routes share `_load_conditions` (raw numbers) but diverge afterwards:
  `GET /conditions` → `format_overview` (raw → human-readable text); `POST
  /recommend` → `rank` (raw → scored ranking). `format_overview` returns each
  factor's band word **plus its raw number**, so the frontend can show the word,
  the figure, or both, and maps each band to its icon (laid out as aligned dot
  points). N/A factors are omitted from a window, mirroring how they drop out of
  the scoring model.
- `is_precipitating` and `precip_type` live in `shared/factors.py` and are called
  by **both** the scorer's per-window scoring and `format_overview` — one definition
  of the precip gate and the snow/mix/rain split, so the overview and the
  recommendation can never disagree about whether it's snowing.
- **`rank` returns cards, not raw scores.** One card per day (best resort that day,
  top 3 days). Each card carries an **8-factor why** — `select_factors` takes the
  top 4 by weight + top 4 by score (static resort factors eligible as fillers),
  and `_describe_factor` reuses `overview.py`'s band-word helpers so the why speaks
  the same vocabulary as the overview (weather factors carry both AM and PM). The
  **contrast** (`_build_contrast`) compares the runner-up resort on 2 factors,
  preferring ones whose band word actually differs so it reads as a real difference.
- **`generate_why` (built).** `POST /recommend` passes `rank`'s cards to
  `explain.generate_why`, which sends all cards' fact packages in **one** Bedrock
  call to **Claude Haiku 4.5**, strictly prompted to use only the supplied facts
  (the deterministic facts are the anti-hallucination guardrail), and attaches a
  `why` paragraph per card. The SDK import and client are lazy so the module loads
  without the dep; any failure (missing SDK/creds, unparseable response) logs and
  falls back to a templated join of the same facts, so the route never fails. The
  live Bedrock call still needs validating against a real endpoint at deploy
  (model access enabled + region), which local tests can't exercise.
- `build_weights` starts from `BASE_WEIGHTS` (also in `shared/factors.py`) and
  bumps individual weights per the preference answers.
- Resort-level factors (lifts, base depth, ability, size, run length, price) are
  scored once by `_resort_scores` and fed into **every** window's weighted average,
  so they differentiate resorts rather than half-days.
- **A few shared-lookup edges are omitted from the diagram** to keep the flow
  readable: `format_overview` also reuses the `is_precipitating` / `precip_type`
  helpers and the resorts' character labels, and the scorer's `_describe_factor`
  reuses `overview.py`'s band-word helpers (both covered in the notes above).
