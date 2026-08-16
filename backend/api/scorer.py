"""
Scoring model — takes cached conditions + user preferences, returns ranked cards.

One card per day: the best resort for that day, ranked best-day-first, capped at 3
(so a 2-day range yields 2 cards, a 5-day range yields the 3 best days). Each card
carries an 8-factor "why" package plus a 2-factor contrast against the runner-up
resort on that day. The prose is added later (Bedrock); this module is fully
deterministic. See ARCHITECTURE.md for the model spec and FACTORS.md for per-factor
detail.

The "why" reuses the overview's band words (imported from overview.py) so the
recommendation and the neutral overview describe conditions with identical vocabulary.
"""

from shared.resorts import (
    RESORTS,
    ABILITY_SCORES, SIZE_SCORES, LENGTH_SCORES, PRICE_SCORES,
    SIZE_LABELS, LENGTH_LABELS, TERRAIN_LABELS, PRICE_LABELS,
)
from shared.factors import (
    build_weights,
    is_precipitating,
    precip_type,
    score_rain_penalty,
    score_wind,
    score_snow_amount,
    score_recent_snow,
    score_base_depth,
    score_snow_quality,
    score_sunniness,
    score_lifts,
)
from overview import (
    _format_window,
    _recent_snow_field,
    _base_depth_field,
    _lifts_field,
)

# Weather factors differ AM vs PM; everything else is one whole-day value.
# Maps each weather factor to its key in the overview's per-window word dict.
WEATHER_KEYS = {
    "rain_penalty": "rain_snow",
    "wind":         "wind",
    "snow_amount":  "snow_amount",
    "snow_quality": "snow_quality",
    "sunniness":    "sunniness",
}

# Static per-resort descriptors, by factor (reuse the overview character words).
STATIC_LABELS = {
    "ability":    TERRAIN_LABELS,
    "size":       SIZE_LABELS,
    "run_length": LENGTH_LABELS,
    "price":      PRICE_LABELS,
}


# --- Per-factor scores (0–1) ---

def _weather_scores(w: dict, resort_static: dict) -> dict:
    """
    Weather factor scores for one AM or PM window. N/A factors are omitted:
    sunniness drops when snowing; snow amount/quality drop when it isn't.
    """
    freezing = w["freezing_level_m"]
    low, high = resort_static["elevation_low"], resort_static["elevation_high"]

    precipitating = is_precipitating(w["precipitation_mm"], w["precipitation_probability"])
    ptype = precip_type(freezing, low, high) if precipitating else "dry"

    scores = {
        "rain_penalty": score_rain_penalty(freezing, low, high) if precipitating else 1.0,
        "wind":         score_wind(w["wind_speed_kmh"]),
    }
    if ptype in ("snow", "mix"):
        scores["snow_amount"]  = score_snow_amount(w["snowfall_cm"])
        scores["snow_quality"] = score_snow_quality(w["temperature_c"])
    else:
        scores["sunniness"] = score_sunniness(w["cloud_cover_pct"])
    return scores


def _resort_scores(resort_key: str, day_data: dict, resort_data: dict, ability: str) -> dict:
    """Whole-day factor scores (identical across AM and PM). The two scraped factors
    (lifts, base depth) are omitted when their data is missing — a missing key drops out
    of _window_score's weighted average, i.e. the factor is N/A rather than scored 0."""
    scores = {
        "recent_snow": score_recent_snow(day_data.get("recent_snow_cm", 0)),
        "ability":     ABILITY_SCORES[ability][resort_key],
        "size":        SIZE_SCORES[resort_key],
        "run_length":  LENGTH_SCORES[resort_key],
        "price":       PRICE_SCORES[resort_key],
    }
    lifts_open, lifts_total = resort_data.get("lifts_open"), resort_data.get("lifts_total")
    if lifts_open is not None and lifts_total:
        scores["lifts"] = score_lifts(lifts_open, lifts_total)
    if resort_data.get("base_depth_cm") is not None:
        scores["base_depth"] = score_base_depth(resort_data["base_depth_cm"])
    return scores


def _window_score(weather: dict, resort: dict, weights: dict) -> float:
    """Weighted average of one window's active factors (weight 0 → excluded)."""
    active = {**weather, **resort}
    numerator   = sum(active[f] * weights[f] for f in active if weights.get(f, 0) > 0)
    denominator = sum(weights[f] for f in active if weights.get(f, 0) > 0)
    return numerator / denominator if denominator > 0 else 0.0


def _combined_scores(am_weather: dict, pm_weather: dict, resort: dict) -> dict:
    """
    One score per factor for the whole day, used for factor selection.
    Weather factors → mean across whichever windows they're active in (so a factor
    that's great one half and poor the other lands fairly in the middle); resort
    factors → their single value.
    """
    combined = dict(resort)
    for f in set(am_weather) | set(pm_weather):
        vals = [wx[f] for wx in (am_weather, pm_weather) if f in wx]
        combined[f] = sum(vals) / len(vals)
    return combined


def score_day(am: float, pm: float) -> float:
    """⅔ better window + ⅓ worse window."""
    better, worse = max(am, pm), min(am, pm)
    return (2 / 3) * better + (1 / 3) * worse


# --- Gates ---

def apply_gates(candidates: list, conditions: dict, preferences: dict) -> list:
    """
    Remove ineligible (resort, day) candidates before scoring.
    Gates:
      - Selwyn excluded for intermediate/advanced skiers
      - Any resort with 0 lifts open is excluded entirely
    """
    ability = preferences.get("ability", "beginner")
    filtered = []
    for c in candidates:
        resort_key = c["resort"]
        if resort_key == "selwyn" and ability in ("intermediate", "advanced"):
            continue
        resort_data = conditions[resort_key]
        # Veto only a *known* zero-open resort (unskiable). Unknown open count (None) is
        # not a veto — we can't call it unskiable, so it stays in with lifts N/A'd.
        if resort_data.get("lifts_total") and resort_data.get("lifts_open") == 0:
            continue
        filtered.append(c)
    return filtered


# --- Factor selection (the 8-factor "why") ---

def select_factors(combined: dict, weights: dict, n: int = 8) -> list:
    """
    Pick the n factors to talk about on a card:
      - top 4 by weight  (what matters most / most to the user), then
      - top 4 by score   (the most positive conditions right now),
    deduped; if that leaves fewer than n (factors ranking high on both lists),
    keep going down both lists until we reach n. Static resort factors (size,
    run length, price) are eligible for the score list even when unweighted —
    they fill the card out with nice-to-know facts. Order is preserved so the
    card leads with importance, then positives, then fillers.
    """
    candidates = list(combined)
    by_weight = sorted(candidates, key=lambda f: (weights.get(f, 0), combined[f], f), reverse=True)
    by_score  = sorted(candidates, key=lambda f: (combined[f], weights.get(f, 0), f), reverse=True)

    selected = []

    def add(f):
        if f not in selected and len(selected) < n:
            selected.append(f)

    for f in by_weight[:4]:
        add(f)
    for f in by_score[:4]:
        add(f)

    i = 4
    while len(selected) < n and (i < len(by_weight) or i < len(by_score)):
        if i < len(by_weight):
            add(by_weight[i])
        if i < len(by_score):
            add(by_score[i])
        i += 1

    return selected


# --- Describing a factor with the overview band words ---

def _describe_factor(factor: str, entry: dict) -> dict:
    """
    Turn a factor name + this card's values into a fact: {factor, ...band words}.
    Weather factors carry both AM and PM (either may be None if N/A that window);
    everything else is one whole-day value.
    """
    resort_key = entry["resort"]

    if factor in WEATHER_KEYS:
        key = WEATHER_KEYS[factor]
        return {
            "factor": factor,
            "am": entry["am_fmt"].get(key),
            "pm": entry["pm_fmt"].get(key),
        }
    if factor == "recent_snow":
        return {"factor": factor, **_recent_snow_field(entry["day_data"].get("recent_snow_cm", 0))}
    if factor == "lifts":
        return {"factor": factor, **_lifts_field(entry["resort_data"]["lifts_open"], entry["resort_data"]["lifts_total"])}
    if factor == "base_depth":
        return {"factor": factor, **_base_depth_field(entry["resort_data"]["base_depth_cm"])}

    # ability / size / run_length / price — static per-resort descriptor
    return {"factor": factor, "label": STATIC_LABELS[factor][resort_key]}


# --- Contrast against the runner-up resort that day ---

def _band_word(value):
    """The band label out of a described-factor value (string, {label:...}, or None)."""
    if value is None or isinstance(value, str):
        return value
    return value.get("label")


def _band_signature(fact: dict) -> tuple:
    """The band word(s) a fact reads as — (am, pm) for weather, (label,) otherwise.
    Used to tell whether a contrast would actually *read* different, not just score
    different (wind 15 vs 30 km/h are both 'fine winds' — a flat contrast in words)."""
    if "am" in fact or "pm" in fact:
        return (_band_word(fact.get("am")), _band_word(fact.get("pm")))
    return (fact.get("label"),)


def _build_contrast(winner: dict, runner_up: dict, weights: dict) -> dict:
    """
    Compare the chosen resort to the runner-up on 2 factors, preferring the
    highest-weighted factors where the chosen resort beats it AND the band words
    differ — so the contrast reads as a real difference, not "fine winds vs fine
    winds". Falls back to same-band wins, then to the biggest score gaps.
    """
    wc, rc = winner["combined"], runner_up["combined"]
    common = [f for f in wc if f in rc]
    wins   = [f for f in common if wc[f] > rc[f]]

    def by_weight_gap(fs):
        return sorted(fs, key=lambda f: (weights.get(f, 0), wc[f] - rc[f], f), reverse=True)

    def band_differs(f):
        return _band_signature(_describe_factor(f, winner)) != _band_signature(_describe_factor(f, runner_up))

    # 1. Wins where the band word actually differs (verbally meaningful).
    chosen = by_weight_gap([f for f in wins if band_differs(f)])[:2]

    # 2. Fall back to other wins (chosen scores higher, same band word).
    if len(chosen) < 2:
        rest = by_weight_gap([f for f in wins if f not in chosen])
        chosen += rest[: 2 - len(chosen)]

    # 3. Ultimate fallback: biggest score gaps among all shared factors.
    if len(chosen) < 2:
        rest = sorted(
            [f for f in common if f not in chosen],
            key=lambda f: (wc[f] - rc[f], weights.get(f, 0), f), reverse=True,
        )
        chosen += rest[: 2 - len(chosen)]

    return {
        "runner_up":     RESORTS[runner_up["resort"]]["name"],
        "runner_up_key": runner_up["resort"],
        "factors": [
            {
                "factor":    f,
                "chosen":    _describe_factor(f, winner),
                "runner_up": _describe_factor(f, runner_up),
            }
            for f in chosen
        ],
    }


# --- Assembling one card ---

def _build_card(winner: dict, runner_up, weights: dict) -> dict:
    selected = select_factors(winner["combined"], weights, 8)
    card = {
        "resort":     RESORTS[winner["resort"]]["name"],
        "resort_key": winner["resort"],
        "date":       winner["date"],
        "day_score":  winner["day_score"],
        "am_score":   winner["am_score"],
        "pm_score":   winner["pm_score"],
        "facts":      [_describe_factor(f, winner) for f in selected],
    }
    if runner_up is not None:
        card["contrast"] = _build_contrast(winner, runner_up, weights)
    return card


def rank(conditions: dict, preferences: dict) -> list:
    """
    Main entry point.
    conditions: DynamoDB data keyed by resort_key.
    preferences: { ability, cost_matters, bigger_resort, longer_runs, snow_pref, selected_dates }
    Returns up to 3 cards — the best resort for each of the top days — each with an
    8-factor "why" package and a runner-up contrast.
    """
    weights = build_weights(preferences)
    ability = preferences.get("ability", "beginner")
    selected_dates = set(preferences["selected_dates"])

    candidates = [
        {"resort": resort_key, "day_data": day_data}
        for resort_key in conditions
        for day_data in conditions[resort_key]["forecast_windows"]
        if day_data["date"] in selected_dates
    ]
    candidates = apply_gates(candidates, conditions, preferences)

    # Score every (resort, day), grouped by date.
    by_date = {}
    for c in candidates:
        resort_key = c["resort"]
        day_data   = c["day_data"]
        resort_static = RESORTS[resort_key]
        resort_data   = conditions[resort_key]

        am_weather = _weather_scores(day_data["am"], resort_static)
        pm_weather = _weather_scores(day_data["pm"], resort_static)
        resort     = _resort_scores(resort_key, day_data, resort_data, ability)

        am = _window_score(am_weather, resort, weights)
        pm = _window_score(pm_weather, resort, weights)

        by_date.setdefault(day_data["date"], []).append({
            "resort":      resort_key,
            "date":        day_data["date"],
            "day_score":   score_day(am, pm),
            "am_score":    am,
            "pm_score":    pm,
            "combined":    _combined_scores(am_weather, pm_weather, resort),
            "day_data":    day_data,
            "resort_data": resort_data,
            "am_fmt":      _format_window(day_data["am"], resort_static),
            "pm_fmt":      _format_window(day_data["pm"], resort_static),
        })

    # Best resort per day, then rank days by that winner's score.
    day_winners = []
    for entries in by_date.values():
        entries.sort(key=lambda e: e["day_score"], reverse=True)
        winner    = entries[0]
        runner_up = entries[1] if len(entries) > 1 else None
        day_winners.append((winner, runner_up))

    day_winners.sort(key=lambda wr: wr[0]["day_score"], reverse=True)

    return [_build_card(winner, runner_up, weights) for winner, runner_up in day_winners[:3]]
