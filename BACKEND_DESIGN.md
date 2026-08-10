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
    FE["Frontend (React on S3 / CloudFront)<br/>renders the overview and the recommendation"]:::built
    AGW["API Gateway (HTTP API)<br/>both routes point to the one API Lambda"]:::store
    EB["EventBridge schedule<br/>fires every few hours"]:::store
    API["API Lambda<br/>handles both routes: returns the overview, and scores the recommendation"]:::built
    INGEST["Ingest Lambda<br/>fetches conditions, writes cache"]:::built
    DDB[("DynamoDB — ConditionsTable<br/>one item per resort: forecast windows + live lift/base snapshot")]:::store
    OM["Open-Meteo<br/>hourly weather forecast, no API key"]:::ext
    OTS["OnTheSnow<br/>live lift status and base depth (scraped)"]:::ext

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
            main["lambda_handler(event, context)<br/>entry point; orchestrates the full ingest and writes each resort to DynamoDB"]:::built
        end

        subgraph ing_ots["ingest/onthesnow.py"]
            ots_all["fetch_all_snapshots()<br/>returns a live lift/base snapshot for all three resorts, keyed by resort"]:::built
            ots_one["fetch_resort_snapshot(resort_key)<br/>fetches one resort's OnTheSnow ski-report page and parses lifts_open, lifts_total, base_depth_cm"]:::todo
        end

        subgraph ing_meteo["ingest/open_meteo.py"]
            meteo_fetch["fetch_resort_forecast(lat, lon, elevation_high, elevation_mid)<br/>fetches one resort's hourly forecast via two elevation-specific calls and merges them"]:::built
            meteo_low["_fetch(lat, lon, elevation, variables, past_days)<br/>performs a single Open-Meteo HTTP GET and returns the raw JSON"]:::built
            meteo_windows["extract_windows(hourly)<br/>slices raw hourly data into per-day AM/PM windows with aggregated factor values"]:::todo
        end

        subgraph ing_shared["shared/resorts.py"]
            resorts_data["RESORTS<br/>static per-resort config: coordinates and low / mid / high elevations"]:::built
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

**Note on the two stubs.** `extract_windows` is on the critical path — its output
shape is exactly what `scorer.score_window` reads back out of DynamoDB, so it
defines the DynamoDB item schema. `fetch_resort_snapshot` does the HTTP fetch
today but raises `NotImplementedError` on the parse until the page HTML is
confirmed.

---

## 3. API Lambda

Triggered by API Gateway. `GET /conditions` just returns the cached overview;
`POST /recommend` loads the cache and runs the scoring model with the user's
preferences. `scorer.rank` is the heart of it — everything below `rank` is the
scoring model from [ARCHITECTURE.md](ARCHITECTURE.md).

```mermaid
flowchart TD
    AGW["API Gateway (HTTP API)"]:::store

    subgraph API["API Lambda"]
        subgraph api_handler["api/handler.py"]
            api_main["lambda_handler(event, context)<br/>entry point; routes GET /conditions and POST /recommend"]:::todo
            api_load["_load_conditions()<br/>reads all resort items from DynamoDB into the conditions dict (shared by both routes)"]:::todo
        end

        subgraph api_overview["api/overview.py"]
            overview["format_overview(conditions)<br/>turns the raw cached values into the human-readable overview (band labels and words); the frontend picks the icons"]:::todo
        end

        subgraph api_scorer["api/scorer.py"]
            rank["rank(conditions, preferences)<br/>builds candidates, filters to selected dates, gates, scores each (resort, day), returns the top 3"]:::built
            gates["apply_gates(candidates, conditions, preferences)<br/>drops ineligible candidates — Selwyn for intermediate/advanced, and any resort with 0% lifts open"]:::built
            window["score_window(window_factors, resort_key, resort_static, day_factors, ability, weights)<br/>weighted average of the active factors for one AM or PM window; N/A factors drop out"]:::built
            day["score_day(am, pm)<br/>combines the two windows into one day score: two-thirds the better window plus one-third the worse"]:::built
            isprecip["_is_precipitating(precip_mm, precip_prob)<br/>true if precip is likely and meaningful — the gate for the whole snow story"]:::built
            ptype["_precip_type(freezing_level_m, elev_low, elev_high)<br/>classifies precipitation as snow, mix, or rain from freezing level vs resort elevations"]:::built
            topf["top_factors(active_scores, weights, preferences, n)<br/>ranks factors by contribution (weight times score) for the explanation text"]:::todo
        end

        subgraph api_factors["shared/factors.py"]
            weights["build_weights(preferences)<br/>turns user preferences into a factor→weight dict (opt-ins plus snowy / bluebird boosts)"]:::built
            subgraph FACTORS["scoring functions — each maps a reading to 0–1"]
                f_rain["score_rain_penalty(...)<br/>1 all-snow, 0.3 mix, 0 all-rain"]:::built
                f_wind["score_wind(...)<br/>1 at 15 km/h or less, down to 0 at 60 km/h or more"]:::built
                f_amount["score_snow_amount(cm)<br/>min(cm / 20, 1)"]:::built
                f_quality["score_snow_quality(temp_c)<br/>cold → 1, marginal → 0.5, warm → 0"]:::built
                f_recent["score_recent_snow(cm)<br/>min(cm / 40, 1)"]:::built
                f_base["score_base_depth(cm)<br/>clamp((cm − 30) / 60, 0, 1)"]:::built
                f_sun["score_sunniness(cloud_pct)<br/>1 − cloud_cover / 100"]:::built
                f_lifts["score_lifts(open, total)<br/>open / total"]:::built
            end
        end

        subgraph api_resorts["shared/resorts.py"]
            rscores["ABILITY_SCORES · SIZE_SCORES · LENGTH_SCORES · PRICE_SCORES<br/>static 0–1 lookup tables for the user-dependent factors"]:::built
        end
    end

    DDB[("DynamoDB — ConditionsTable")]:::store

    AGW -->|"invokes on each request"| api_main
    api_main -->|"GET — load the cache"| api_load
    api_main -->|"GET — then format for display"| overview
    api_main -->|"POST — load the cache"| api_load
    api_main -->|"POST — then score with prefs"| rank
    api_load -->|"read all resort items"| DDB

    rank -->|"prefs → factor weights"| weights
    rank -->|"drop ineligible (resort, day) combos"| gates
    rank -->|"score each half-day (AM and PM)"| window
    rank -->|"combine the two windows"| day
    rank -.->|"planned — build the explanation"| topf

    window -->|"is precip likely and meaningful?"| isprecip
    window -->|"if precipitating, classify the type"| ptype
    window -->|"score each active factor"| FACTORS
    window -->|"look up user-dependent scores"| rscores

    classDef built fill:#d3f9d8,stroke:#2b8a3e,color:#000;
    classDef todo fill:#fff3bf,stroke:#e67700,color:#000,stroke-dasharray: 5 3;
    classDef store fill:#f3e8ff,stroke:#7048e8,color:#000;
```

**Notes.**
- The two routes share `_load_conditions` (raw numbers) but diverge afterwards:
  `GET /conditions` → `format_overview` (raw → human-readable text); `POST
  /recommend` → `rank` (raw → scored ranking). `format_overview` returns the band
  words; the frontend maps each band to its icon.
- `build_weights` starts from `BASE_WEIGHTS` (also in `shared/factors.py`) and
  bumps individual weights per the preference answers.
- `top_factors` is written but its mapping from factor names to plain-English
  explanation strings is a TODO, and `rank` doesn't call it yet — hence the dashed
  arrow. Wiring it in is what turns each result into an expandable "why" card.
- `score_window` reads the resort-level values (lifts, base depth, ability, size,
  run length, price) once and feeds them into every window's average, so they
  differentiate resorts rather than days.
