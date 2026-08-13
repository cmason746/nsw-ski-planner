"""
Overview formatting — turns the raw cached conditions into the neutral,
preference-independent overview shown at app-flow step 2.

No scoring or weighting here (that's the recommendation): this maps each raw
reading to a plain-English band word per FACTORS.md. Every field carries the raw
number alongside its label so the frontend can show the figure, the word, or both,
and pick its own icons. Words are laid out as aligned dot points on the frontend.

Structure returned, per resort:
  { name, lifts, base_depth, character, days: [ { date, recent_snow, am, pm } ] }
where am/pm hold the per-window weather words. Snow factors are omitted when not
snowing (a dry window has no `snow_amount`/`snow_quality`), but `sunniness` is shown
on every window — including snow days — since the overview is informational, unlike
the scorer which drops sunniness when snowing. Frontend branches on the window
`type` field, not on which keys are present.
"""

from shared.resorts import RESORTS, SIZE_LABELS, LENGTH_LABELS, TERRAIN_LABELS
from shared.factors import is_precipitating, precip_type


def format_overview(conditions: dict) -> dict:
    """
    conditions: DynamoDB data keyed by resort_key (as returned by _load_conditions).
    Returns the display-ready overview keyed by resort_key.
    """
    return {
        resort_key: {
            "name":       RESORTS[resort_key]["name"],
            "lifts":      _lifts_field(data["lifts_open"], data["lifts_total"]),
            "base_depth": _base_depth_field(data["base_depth_cm"]),
            "character":  _character(resort_key),
            "elevations": _elevations_field(RESORTS[resort_key]),
            "days": [
                {
                    "date":        day["date"],
                    "recent_snow": _recent_snow_field(day["recent_snow_cm"]),
                    "am":          _format_window(day["am"], RESORTS[resort_key]),
                    "pm":          _format_window(day["pm"], RESORTS[resort_key]),
                }
                for day in data["forecast_windows"]
            ],
        }
        for resort_key, data in conditions.items()
    }


# --- Per-window weather ---

def _format_window(w: dict, resort_static: dict) -> dict:
    """One AM or PM window → display words. Same active/N-A logic as score_window."""
    freezing = w["freezing_level_m"]
    low  = resort_static["elevation_low"]
    high = resort_static["elevation_high"]

    precipitating = is_precipitating(w["precipitation_mm"], w["precipitation_probability"])
    ptype = precip_type(freezing, low, high) if precipitating else "dry"

    prob = round(w["precipitation_probability"])
    kmh  = round(w["wind_speed_kmh"])
    window = {
        # Probability word is always shown (kept even on dry windows — "unlikely"
        # reads less severe than nothing; frontend decides how to pair it with rain_snow).
        "precip_probability": {
            "pct":   prob,
            "label": _precip_prob_label(prob),
        },
        # `type` is the stable machine value ("dry"/"snow"/"mix"/"rain"); `rain_snow`
        # is the display string. Frontend branches on `type`, shows `rain_snow`.
        "type": ptype,
        "rain_snow": _rain_snow_label(ptype, freezing),
        "wind": {
            "kmh":   kmh,
            "label": _wind_label(kmh),
        },
    }

    # Snow amount + quality — only when some of the resort is getting snow.
    if ptype in ("snow", "mix"):
        window["snow_amount"]  = _snow_amount_field(w["snowfall_cm"], ptype, freezing)
        window["snow_quality"] = {
            "temp_c": round(w["temperature_c"]),
            "label":  _snow_quality_label(w["temperature_c"]),
        }

    # Sunniness — always shown on the overview. NOTE: this diverges from the scorer,
    # which drops sunniness when snowing so powder days aren't penalised for lack of
    # sun. The overview is informational, not scored, so "cloudy" on a snow day is
    # just honest context (and a mix day can be genuinely partly cloudy). Because snow
    # windows now also carry `sunniness`, the frontend must branch on `type`, not on
    # which keys are present.
    sunniness_pct = round(100 - w["cloud_cover_pct"])
    window["sunniness"] = {
        "sunniness_pct": sunniness_pct,
        "label":         _sunniness_label(sunniness_pct),
    }

    return window


def _precip_prob_label(pct: float) -> str:
    if pct < 40:
        return "unlikely"
    if pct < 60:
        return "maybe"
    if pct < 80:
        return "likely"
    return "very likely"


def _rain_snow_label(ptype: str, freezing_level_m: float) -> str:
    if ptype == "dry":
        return "no precipitation forecast"
    if ptype == "snow":
        return "snow across whole resort"
    if ptype == "rain":
        return "rain across whole resort"
    return f"snow up high, rain below ~{_round_to_10(freezing_level_m)} m"  # mix


def _snow_amount_field(cm: float, ptype: str, freezing_level_m: float) -> dict:
    field = {"cm": cm, "label": _snow_amount_label(cm)}
    if ptype == "mix":
        field["note"] = f"rain below ~{_round_to_10(freezing_level_m)} m"
    return field


def _snow_amount_label(cm: float) -> str:
    if cm < 3:
        return "dusting"
    if cm <= 10:
        return "decent"
    return "dump"


def _snow_quality_label(temp_c: float) -> str:
    # Bands match score_snow_quality so the words track the score.
    # "quality" is in each label so the frontend reads e.g. "-5°C = dry & light quality snow".
    if temp_c <= -3:
        return "dry & light quality snow"
    if temp_c <= -0.5:
        return "OK quality snow"
    return "wet & sticky quality snow"


def _wind_label(kmh: float) -> str:
    if kmh <= 30:
        return "fine winds"
    if kmh <= 50:
        return "windy, some lifts may be on hold"
    return "very windy, lifts likely to be on hold"


def _sunniness_label(sunniness_pct: float) -> str:
    if sunniness_pct > 70:
        return "sunny"
    if sunniness_pct >= 40:
        return "partly cloudy"
    return "cloudy"


# --- Per-day ---

def _recent_snow_field(cm: float) -> dict:
    if cm < 10:
        label = "not much recent snow"
    elif cm <= 40:
        label = "a bit of recent snow"
    else:
        label = "a lot of fresh snow"
    return {"cm": round(cm), "label": label}


# --- Per-resort (live snapshot + static character) ---

def _lifts_field(open_count, total_count) -> dict:
    open_count, total_count = int(open_count), int(total_count)
    return {
        "open":  open_count,
        "total": total_count,
        # pct disambiguates the contrast: "13 of 15 (87%)" beats "38 of 45 (84%)"
        # on coverage even though the raw count is smaller. Label stays count-only.
        "pct":   round(100 * open_count / total_count) if total_count else 0,
        "label": f"{open_count} of {total_count} open",
    }


def _base_depth_field(cm: float) -> dict:
    if cm <= 30:
        label = "thin base depth, patchy coverage"
    elif cm <= 60:
        label = "ok base depth and coverage"
    elif cm <= 90:
        label = "good base depth and decent coverage"
    else:
        label = "great base depth and excellent coverage"
    return {"cm": round(cm), "label": label}


def _character(resort_key: str) -> list:
    return [
        SIZE_LABELS[resort_key],
        LENGTH_LABELS[resort_key],
        TERRAIN_LABELS[resort_key],
    ]


def _elevations_field(resort_static: dict) -> dict:
    """Lift-served elevation range (m ASL) — displayed as a low–high range. Static per
    resort; helps users read the freezing-level rain/snow split against the mountain."""
    return {
        "low":  resort_static["elevation_low"],
        "high": resort_static["elevation_high"],
    }


# --- helpers ---

def _round_to_10(m: float) -> int:
    """Round a freezing-level height to the nearest 10 m for a clean '~1700 m' read."""
    return int(round(m / 10.0) * 10)
