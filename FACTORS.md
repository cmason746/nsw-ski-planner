# Decision Factors

How each factor works — **what it is**, **why we care**, **where the data comes
from**, and **how it scores**. Grouped the way the overview presents them:
weather & snow → lifts → resort character → cost.

**Scoring in brief:** every scored factor maps to **0–1** (0 = bad for skiing,
1 = ideal) and carries a **weight out of 10** (shown per factor below). The
recommendation is a weighted average of the active factors per (resort, day);
the overall model lives in [ARCHITECTURE.md](ARCHITECTURE.md). Static resort
figures live in [RESORT_DATA.md](RESORT_DATA.md).

## Contents

- **Weather & snow**
  - The snow story: precipitation → rain or snow → how much snow → snow quality
  - Recent snow
  - Base depth
  - Wind
  - Sunniness
- **Lifts** — open-lift %
- **Resort character** — size, ability level, run length
- **Cost** — lift ticket price

## Conventions

- **Time windows.** Every forecast factor is summarised per day into two windows
  matching lift hours: **morning 08:30–12:30**, **afternoon 12:30–16:30**.
  (Open-Meteo is hourly on-the-hour, so boundaries map to whole-hour buckets in
  code — exact rounding settled at build time.)
- **Aggregation within a window** depends on the reading: **amounts** (precip,
  snowfall) → **sum**; **intensities/likelihoods** (wind, precip probability) →
  **max**; **level readings** (freezing level, temperature, cloud cover) → **mean**.
- **Forecast vs live snapshot.** Most factors are per-day forecasts. Two —
  **open-lift %** and **base depth** — are current live snapshots (OnTheSnow):
  the same value applies across all days, not per day.

---

# Weather & snow

Forecast per AM/PM window — except base depth, a live snapshot, grouped here
because it's snow on the ground.

## The snow story

Four factors that together answer *"will there be good snow?"* They're **gated** —
each depends on the one before:

```
Is precip likely AND meaningful?  (max probability > 40%  AND  summed precip > 1 mm)
├─ No  → dry window: rain/snow = 1 (not-rain, good), snow amount = N/A, quality = N/A
└─ Yes → Is it snowing?  (freezing level vs resort elevation)
         ├─ Snow (all or partial) → snow amount and quality apply
         └─ All rain → rain/snow = 0 (penalty); snow amount = N/A, quality = N/A
```

The probability gate (`> 40%`, i.e. at least "maybe" likely) means we don't run
the rain/snow analysis on days where precip is forecast but improbable.

So **snow amount and snow quality only apply when it's actually snowing.** On a
dry or rain window they're N/A and drop out of the weighting — a clear day is
never penalised for simply lacking current snowfall.

**Inactive-factor rule:** when a factor is **N/A** (e.g. snow quality on a dry
day) it **drops out of the weighting** — it is *not* scored 0. This stops a clear
bluebird day being punished on an axis that doesn't apply.

### Precipitation — is anything falling?
- **What:** how much precipitation is forecast, and how likely.
- **Why:** the gate for the whole snow story — nothing falls, nothing to classify.
- **Data:** Open-Meteo `precipitation` (mm, **summed** per window) and
  `precipitation_probability` (%, **max** per window). Probability → words:
  `<40` unlikely, `40–59` maybe, `60–79` likely, `≥80` very likely (per window).
- **Score:** **not scored** — informational only. Its content feeds the next two
  factors (amount → how much snow; type → rain or snow).
- **Weight:** none (informational).

### Rain or snow? (freezing level)
- **What:** whether precip falls as snow or rain, and where on the mountain the
  line sits.
- **Why:** rain wrecks skiing — the same precip is great as snow, miserable as
  rain.
- **Data:** Open-Meteo `freezing_level_height` (m ASL), **mean** per window,
  compared to the resort's lift-served range. Only runs when precip is **likely
  and meaningful** — window max probability **> 40%** *and* summed precip
  **> 1 mm**. Otherwise the window is treated as dry.

  | Resort | Lowest lifted | Highest lifted |
  |---|---|---|
  | Perisher | 1605 m | 2042 m |
  | Thredbo | 1365 m | 2037 m |
  | Selwyn | 1492 m | 1614 m |

- **Classification:** freezing level ≤ lowest → **snow across whole resort**;
  between low and high → **snow up high, rain below** (report the switch height);
  ≥ highest → **rain across whole resort**.
- **Score (the rain penalty):** all snow → **1**; no precip / bluebird → **1**;
  mix → **0.3** (still pretty miserable); all rain → **0**.
- **Weight:** 10 (always) — the heaviest factor; rain is a big deal.
  - _Bluebird vs powder is handled by weighting, not here: a powder-seeker weights
    snow amount up; a clear-day lover benefits via sunniness. This factor just
    rewards "not rain."_

### How much snow
- **What:** fresh snowfall during the window.
- **Why:** more fresh snow = better skiing.
- **Data:** Open-Meteo `snowfall` (cm) at the **highest lifted point** (the snow
  zone), **summed** per window. Reported by zone: all-snow → the figure; mix →
  figure + "rain below ~X m"; all-rain → no snow figure.
- **Score:** `min(cm / 20, 1)` — 0 cm → 0, ≥ 20 cm → 1, linear. **Only applies
  when it's snowing** (all-snow or mix); on a dry or rain window it's N/A and
  drops from the weighting (not scored 0).
- **Weight:** 7 baseline → **9** if the user picks "snowy".

### Snow quality (temperature)
- **What:** whether falling snow is dry/good or wet/sticky, inferred from
  temperature.
- **Why:** the same amount of snow skis completely differently cold vs
  near-freezing.
- **Data:** Open-Meteo `temperature_2m` at **mid-mountain**, **mean** per window
  (one mid reading is representative; AU verticals are small).

  | Resort | Mid-mountain |
  |---|---|
  | Perisher | 1824 m |
  | Thredbo | 1701 m |
  | Selwyn | 1553 m |

  Bands: `≤ −3°C` dry/good; `−3 to −0.5°C` OK; `≥ −0.5°C` wet/sticky.
- **Score:** dry/good → **1**; OK → **0.5**; wet/sticky → **0**.
- **Weight:** 5 (when snowing).
- **Only applies when it's snowing** — otherwise N/A (drops from weighting).
  _(Not modelled: surface softening on a warm, non-snowing day.)_

## Recent snow
- **What:** snow accumulated in the ~2 days before you arrive.
- **Why:** fresh snow already on the ground — freshness/cover. Distinct from snow
  *on* the day and from total base depth.
- **Data:** Open-Meteo `snowfall` at the **highest lifted point**, **summed** from
  **00:00 two days before** the selected date up to **lift-open (08:30)** on the
  day — full hours, includes overnight. (Uses `past_days` + forecast in one call.)
- **Score:** `min(cm / 40, 1)` — 0 cm → 0, ≥ 40 cm → 1, linear.
- **Weight:** 7 baseline → **10** if the user picks "snowy".

## Base depth  *(live snapshot)*
- **What:** total snowpack on the ground right now.
- **Why:** thin base = patchy/rocks; deep base = well covered.
- **Data:** OnTheSnow reported base depth, all three resorts (same page as lifts),
  in cm. A current snapshot — same across all days.
- **Score:** `clamp((cm − 30) / 60, 0, 1)` — ≥ 90 cm → 1, ≤ 30 cm → 0, linear.
- **Weight:** 6 (always).

## Wind
- **What:** sustained ridgetop wind.
- **Why:** strong wind closes lifts and makes skiing unpleasant.
- **Data:** Open-Meteo `wind_speed_120m` (ridgetop height; gusts ignored — they
  spike and overstate), **max** per window. Bands: `> 50` "lifts likely on hold";
  `30–50` "windy, some may hold"; `≤ 30` fine.
- **Score:** `clamp((60 − wind) / 45, 0, 1)` — ≤ 15 km/h → 1, ≥ 60 km/h → 0.
- **Weight:** 8 (always).
- Direction / resort aspect not included (data unavailable + too complex).

## Sunniness (sun vs cloud)
- **What:** how sunny vs cloudy the window is — the "bluebird" factor.
- **Why:** a bluebird day is really about *sun* — clear skies make for a lovely
  day and good light. (Also shown in the overview as sunny/cloudy.)
- **Data:** Open-Meteo `cloud_cover` (%), **mean** per window.
- **Score (0–1):** `1 − mean(cloud_cover)/100` — clear sky → 1, fully overcast → 0.
- **Overview display** (by sunniness %, i.e. `100 − mean cloud cover`):
  | Sunniness | Label | Icon |
  |---|---|---|
  | > 70% | sunny | ☀️ |
  | 40–70% | partly cloudy | ⛅ |
  | < 40% | cloudy | ☁️ |
- **Weight:** 7 baseline → **10** if the user picks "bluebird". **N/A when it's
  snowing** during the window — it's cloudy anyway, and a powder day shouldn't be
  marked down on sun; drops from the weighting for everyone. (The bluebird
  preference still steers correctly, by *rewarding* sunny days rather than
  punishing snow days.)

---

# Lifts

## Open-lift %  *(live snapshot)*
- **What:** proportion of the resort's lifts currently open.
- **Why:** closures shrink the accessible mountain.
- **Data:** OnTheSnow "X of Y open" for all three resorts (one parser, consistent
  format). Current / next-day snapshot — same across days.
  - Fallbacks if needed: official Perisher & Thredbo pages; Selwyn has no
    structured official source, which is why OnTheSnow is the primary.
  - It's a **nowcast**; the *forecast* angle on lift availability is covered by
    **Wind**.
- **Score:** `open ÷ total` — 100% open → 1, none → 0. No floor.
- **Gate:** **0% open → the resort is vetoed entirely** (unskiable) — see
  [ARCHITECTURE.md](ARCHITECTURE.md).
- **Weight:** 7 (always).

---

# Resort character  *(static)*

Static per-resort facts (see [RESORT_DATA.md](RESORT_DATA.md)). Used two ways: a
short overview descriptor ("Selwyn: small, beginner-friendly"), and
preference-weighting in the recommendation. Their scores are **user-dependent**,
so they're set with the preferences step (see [ARCHITECTURE.md](ARCHITECTURE.md)).

## Size
- **What / why:** total slope length (km) — bigger resort = more terrain/variety.
- **Data:** Perisher 65, Thredbo 52, Selwyn 10.
- **Score (0–1):** min-max normalised across the three (applies only if the user
  wants a bigger resort): Perisher **1.0**, Thredbo **0.76**, Selwyn **0**.
- **Weight:** 6 (only if the user wants a bigger resort).

## Ability level
- **What / why:** how well the resort suits the skier's level. Not raw proportion
  — the big resorts (Perisher/Thredbo) have lots of beginner/intermediate terrain
  in absolute terms, so they score well across levels.
- **Data:** run split % ([RESORT_DATA.md](RESORT_DATA.md)); scores hand-set by
  Charlotte from ski judgment.
- **Score (0–1)** by user's level (Selwyn excluded for intermediate/advanced):
  | Level | Perisher | Thredbo | Selwyn |
  |---|---|---|---|
  | Beginner | 0.7 | 0.6 | 0.90 |
  | Intermediate | 0.8 | 0.8 | — |
  | Advanced | 0.8 | 0.9 | — |
- **Weight:** 6 (always).

## Run length
- **What / why:** longest run (km) — some skiers prefer long runs.
- **Data:** Thredbo ~5.9, Perisher ~4, Selwyn ~0.8 (approx; the order is what
  matters).
- **Score (0–1):** min-max normalised (applies only if the user wants longer
  runs): Thredbo **1.0**, Perisher **0.63**, Selwyn **0**.
- **Weight:** 7 (only if the user wants longer runs).

---

# Cost

## Lift ticket price
- **What / why:** single-day adult ticket — cheaper is better for cost-conscious
  users.
- **Data:** shown as "roughly $X"; what matters is the order, priciest to
  cheapest — Perisher, Thredbo, Selwyn ([RESORT_DATA.md](RESORT_DATA.md)).
- **Score (0–1):** inverted min-max normalised so cheapest = 1 (applies only if
  cost matters): Selwyn **1.0**, Thredbo **0.14**, Perisher **0**.
- **Weight:** 8 (only if cost matters).
