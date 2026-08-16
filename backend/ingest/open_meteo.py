"""
Fetches forecast data from Open-Meteo for all three resorts.
Returns raw hourly data; the handler slices it into AM/PM windows.
No API key required.
"""

import json
from datetime import datetime, date, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

from shared.dates import sydney_today

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

FORECAST_DAYS = 10  # see ARCHITECTURE.md — forecast horizon decision

# Fetched at highest lifted point — snowfall meaningfully depends on elevation
HIGH_ELEVATION_VARIABLES = [
    "precipitation",
    "precipitation_probability",
    "snowfall",
    "freezing_level_height",
    "wind_speed_120m",
    "cloud_cover",
]

# Fetched at mid-mountain — temperature for snow quality depends on elevation
MID_ELEVATION_VARIABLES = [
    "temperature_2m",
]


def _fetch(lat: float, lon: float, elevation: float, variables: list, past_days: int) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "elevation": elevation,
        "hourly": ",".join(variables),
        "timezone": "Australia/Sydney",
        "forecast_days": FORECAST_DAYS,
        "past_days": past_days,
    }
    url = f"{OPEN_METEO_URL}?{urlencode(params)}"
    with urlopen(url, timeout=10) as response:  # raises HTTPError on non-2xx
        return json.loads(response.read())


def fetch_resort_forecast(
    lat: float,
    lon: float,
    elevation_high: float,
    elevation_mid: float,
    past_days: int = 2,
) -> dict:
    """
    Fetch hourly forecast for a single resort using two elevation-specific calls.
    Returns a merged hourly dict with all variables keyed by name.
    past_days=2 captures overnight snowfall for the recent-snow factor.
    """
    high = _fetch(lat, lon, elevation_high, HIGH_ELEVATION_VARIABLES, past_days)
    mid = _fetch(lat, lon, elevation_mid, MID_ELEVATION_VARIABLES, past_days)

    merged = high.copy()
    merged["hourly"]["temperature_2m"] = mid["hourly"]["temperature_2m"]
    return merged


AM_HOURS = [9, 10, 11, 12]
PM_HOURS = [13, 14, 15, 16]


def extract_windows(hourly: dict) -> list[dict]:
    """
    Slice raw hourly Open-Meteo data into per-day AM (09:00–13:00) and PM (13:00–17:00) windows.
    Returns one dict per forecast day (today onward), each with aggregated factor values.
    Past-days data is included in the fetch only to enable recent_snow_cm calculation.
    """
    times = [datetime.fromisoformat(t) for t in hourly["time"]]

    # Group hourly array indices by date string and hour
    by_date: dict[str, dict[int, int]] = {}
    for i, dt in enumerate(times):
        by_date.setdefault(dt.strftime("%Y-%m-%d"), {})[dt.hour] = i

    # Sydney-local today, not the Lambda's UTC date — the day keys above are Sydney
    # local (Open-Meteo is queried with timezone=Australia/Sydney), so "today" must be
    # too, or the first 10 hours of each Sydney day would keep yesterday as day 0.
    today = sydney_today()
    forecast_dates = sorted(d for d in by_date if d >= today)

    return [
        {
            "date": day_str,
            "recent_snow_cm": _recent_snow(hourly, by_date, day_str),
            "am": _aggregate_window(hourly, by_date.get(day_str, {}), AM_HOURS),
            "pm": _aggregate_window(hourly, by_date.get(day_str, {}), PM_HOURS),
        }
        for day_str in forecast_dates
    ]


def _aggregate_window(hourly: dict, day_hours: dict[int, int], hours: list[int]) -> dict:
    indices = [day_hours[h] for h in hours if h in day_hours]

    def vals(key):
        return [hourly[key][i] for i in indices]

    def mean(lst):
        return sum(lst) / len(lst) if lst else 0.0

    return {
        "snowfall_cm":               sum(vals("snowfall")),
        "precipitation_mm":          sum(vals("precipitation")),
        "precipitation_probability":  max(vals("precipitation_probability"), default=0),
        "freezing_level_m":          mean(vals("freezing_level_height")),
        "temperature_c":             mean(vals("temperature_2m")),
        "wind_speed_kmh":            max(vals("wind_speed_120m"), default=0.0),
        "cloud_cover_pct":           mean(vals("cloud_cover")),
    }


def _recent_snow(hourly: dict, by_date: dict[str, dict[int, int]], day_str: str) -> float:
    """Sum snowfall from 00:00 two days before day_str up to 08:00 on day_str (inclusive)."""
    day = date.fromisoformat(day_str)

    total = 0.0
    for days_back in (2, 1):
        past_str = (day - timedelta(days=days_back)).isoformat()
        for i in by_date.get(past_str, {}).values():
            total += hourly["snowfall"][i]

    for h in range(9):  # 00:00 to 08:00 inclusive
        if h in by_date.get(day_str, {}):
            total += hourly["snowfall"][by_date[day_str][h]]

    return total
