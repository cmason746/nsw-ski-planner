"""
Factor weights and scoring functions.
All scores return a float 0.0–1.0, or None when the factor is N/A.
See FACTORS.md for the full spec.
"""

# Base weights (out of 10). User preferences can boost some; see build_weights().
BASE_WEIGHTS = {
    "rain_penalty":   10,
    "wind":            8,
    "lifts":           7,
    "ability":         6,
    "base_depth":      6,
    "snow_quality":    5,
    "snow_amount":     7,
    "recent_snow":     7,
    "sunniness":       7,
    "price":           0,  # off unless user opts in
    "size":            0,  # off unless user opts in
    "run_length":      0,  # off unless user opts in
}


def build_weights(preferences: dict) -> dict:
    """
    Adjust BASE_WEIGHTS from user preferences.
    preferences keys: ability, cost_matters, bigger_resort, longer_runs, snow_pref
    snow_pref: "snowy" | "bluebird" | "dont_mind"
    """
    weights = BASE_WEIGHTS.copy()

    if preferences.get("cost_matters"):
        weights["price"] = 8
    if preferences.get("bigger_resort"):
        weights["size"] = 6
    if preferences.get("longer_runs"):
        weights["run_length"] = 7

    snow_pref = preferences.get("snow_pref", "dont_mind")
    if snow_pref == "snowy":
        weights["snow_amount"] = 9
        weights["recent_snow"] = 10
    elif snow_pref == "bluebird":
        weights["sunniness"] = 10

    return weights


# --- Precipitation classification (shared by the scorer and the overview) ---
# Defined once here so the recommendation and the overview always agree on whether
# a window counts as precipitating, and whether it's snow / mix / rain.

def is_precipitating(precip_mm: float, precip_prob: float) -> bool:
    """
    True when precip is likely and meaningful — the gate for the whole snow story.
    precip_mm is summed over the window; precip_prob is the max (both from extract_windows).
    """
    # >= 40 matches the "maybe" probability band boundary (see _precip_prob_label) so the
    # gate and the displayed wording agree at exactly 40%.
    return precip_prob >= 40 and precip_mm > 1


def precip_type(freezing_level_m: float, elevation_low: float, elevation_high: float) -> str:
    """
    Classify precipitation as 'snow', 'mix', or 'rain' from freezing level vs resort elevations.
    Only meaningful when is_precipitating() is True.
      snow: freezing level at or below the lowest lift — whole resort getting snow.
      mix:  between low and high — snow up top, rain below.
      rain: at or above the highest lift — whole resort getting rain.
    """
    if freezing_level_m <= elevation_low:
        return "snow"
    if freezing_level_m >= elevation_high:
        return "rain"
    return "mix"


# --- Individual scoring functions ---

def score_rain_penalty(freezing_level: float, elevation_low: float, elevation_high: float) -> float:
    if freezing_level <= elevation_low:
        return 1.0   # all snow
    if freezing_level >= elevation_high:
        return 0.0   # all rain
    return 0.3       # mix


def score_wind(wind_speed_kmh: float) -> float:
    return max(0.0, min(1.0, (60 - wind_speed_kmh) / 45))


def score_snow_amount(snowfall_cm: float) -> float:
    return min(snowfall_cm / 20, 1.0)


def score_recent_snow(snowfall_cm: float) -> float:
    return min(snowfall_cm / 40, 1.0)


def score_base_depth(depth_cm: float) -> float:
    return max(0.0, min((depth_cm - 30) / 60, 1.0))


def score_snow_quality(temp_c: float) -> float:
    if temp_c <= -3:
        return 1.0   # dry/good
    if temp_c <= -0.5:
        return 0.5   # ok
    return 0.0       # wet/sticky


def score_sunniness(cloud_cover_pct: float) -> float:
    return 1.0 - (cloud_cover_pct / 100)


def score_lifts(open_count: int, total_count: int) -> float:
    if total_count == 0:
        return 0.0
    return open_count / total_count
