"""
Scrapes live lift status and base depth from OnTheSnow.
Returns a snapshot (not a forecast) — the same value is used across all days.

OnTheSnow is a Next.js app: it server-renders every page with all its data
embedded in a single `<script id="__NEXT_DATA__">` JSON blob. We parse that blob
rather than the rendered HTML — it's the resort's structured data (lift counts,
depths in cm) straight from their API, so it's far less fragile than scraping
divs and needs no unit conversion.

Accepted fragility: the JSON shape may still change. This is a short-lived app and
OnTheSnow is the only source covering all three resorts in one consistent format.
"""

import json
import re
from urllib.request import Request, urlopen

RESORT_URLS = {
    "perisher": "https://www.onthesnow.com/new-south-wales/perisher/skireport",
    "thredbo":  "https://www.onthesnow.com/new-south-wales/thredbo-alpine-resort/skireport",
    "selwyn":   "https://www.onthesnow.com/new-south-wales/selwyn-snowfields/skireport",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ski-planner/1.0)"
}

# Pulls the JSON out of <script id="__NEXT_DATA__" type="application/json">...</script>
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)

# Depth comes back per elevation band; not all are always reported. Prefer the
# thinnest reported (base = worst-covered, most decision-relevant), fall back up.
_DEPTH_PREFERENCE = ("base", "middle", "summit")


def fetch_resort_snapshot(resort_key: str) -> dict:
    """
    Fetch and parse live conditions for one resort.
    Returns: { lifts_open, lifts_total, base_depth_cm }  — all numeric.
    Raises on fetch failure (urllib) or parse failure (ValueError).
    """
    url = RESORT_URLS[resort_key]
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=10) as response:  # raises HTTPError on non-2xx
        html = response.read().decode("utf-8", errors="replace")

    full_resort = _extract_full_resort(html, resort_key)

    lifts = full_resort.get("lifts") or {}
    lifts_open = lifts.get("open")
    lifts_total = lifts.get("total")
    if lifts_open is None or lifts_total is None:
        raise ValueError(f"{resort_key}: lift counts missing from OnTheSnow data")

    return {
        "lifts_open": lifts_open,
        "lifts_total": lifts_total,
        "base_depth_cm": _pick_depth(full_resort.get("depths") or {}, resort_key),
    }


def _extract_full_resort(html: str, resort_key: str) -> dict:
    """Pull the fullResort object out of the page's __NEXT_DATA__ JSON blob."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise ValueError(f"{resort_key}: __NEXT_DATA__ blob not found — page structure changed")

    data = json.loads(match.group(1))
    try:
        return data["props"]["pageProps"]["fullResort"]
    except (KeyError, TypeError):
        raise ValueError(f"{resort_key}: fullResort missing from __NEXT_DATA__ — shape changed")


def _pick_depth(depths: dict, resort_key: str) -> float:
    """First reported depth (cm) in base → middle → summit order."""
    for band in _DEPTH_PREFERENCE:
        value = depths.get(band)
        if value is not None:
            return value
    raise ValueError(f"{resort_key}: no base depth reported in any elevation band")


def fetch_all_snapshots() -> dict:
    """Fetch snapshots for all three resorts. Returns { resort_key: snapshot_dict }."""
    return {key: fetch_resort_snapshot(key) for key in RESORT_URLS}
