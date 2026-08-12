RESORTS = {
    "perisher": {
        "name": "Perisher",
        "lat": -36.4058,
        "lon": 148.4085,
        "elevation_low": 1605,
        "elevation_high": 2042,
        "elevation_mid": 1824,
    },
    "thredbo": {
        "name": "Thredbo",
        "lat": -36.5047,
        "lon": 148.3056,
        "elevation_low": 1365,
        "elevation_high": 2037,
        "elevation_mid": 1701,
    },
    "selwyn": {
        "name": "Selwyn",
        "lat": -35.9083,
        "lon": 148.4500,
        "elevation_low": 1492,
        "elevation_high": 1614,
        "elevation_mid": 1553,
    },
}

# Static scores — set from ski judgment, not data (see FACTORS.md)
ABILITY_SCORES = {
    "beginner":     {"perisher": 0.7, "thredbo": 0.6, "selwyn": 0.9},
    "intermediate": {"perisher": 0.8, "thredbo": 0.8, "selwyn": None},
    "advanced":     {"perisher": 0.8, "thredbo": 0.9, "selwyn": None},
}

# min-max normalised across the three resorts (see FACTORS.md)
SIZE_SCORES    = {"perisher": 1.0, "thredbo": 0.76, "selwyn": 0.0}
LENGTH_SCORES  = {"perisher": 0.63, "thredbo": 1.0,  "selwyn": 0.0}

# Inverted so cheapest = 1.0
PRICE_SCORES   = {"perisher": 0.0, "thredbo": 0.14, "selwyn": 1.0}
PRICE_LABELS   = {"perisher": "~AU$280", "thredbo": "~AU$260", "selwyn": "~AU$135"}

# Static overview descriptors — the plain words shown on the neutral overview
# (preference-independent resort character). See FACTORS.md.
SIZE_LABELS    = {
    "perisher": "largest ski resort in Australia",
    "thredbo":  "large ski resort",
    "selwyn":   "small ski resort",
}
LENGTH_LABELS  = {
    "perisher": "medium-length runs",
    "thredbo":  "long runs",
    "selwyn":   "short runs",
}
TERRAIN_LABELS = {
    "perisher": "suited to all abilities",
    "thredbo":  "suited to all abilities",
    "selwyn":   "beginner-friendly resort",
}
