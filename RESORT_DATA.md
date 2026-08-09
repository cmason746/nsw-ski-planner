# Resort static data (resort character & price)

Compiled per-resort static data for the **resort character** factors (size,
ability level, run length) and **lift ticket price**. Not live — compiled by
hand, with sources + dates. Becomes a structured data file (JSON) when we build.

**Primary source:** skiresort.com (consistent cross-resort format).
**Compiled:** 2026-08-06.

## Terrain & price

| Resort | Total slope (km) | Easy | Intermediate | Advanced | Longest run | Adult 1-day (roughly) |
|---|---|---|---|---|---|---|
| Perisher | 65 | 25 km (38%) | 30 km (47%) | 10 km (15%) | ~4 km | ~AU$280 |
| Thredbo | 52 | 15 km (29%) | 25 km (48%) | 12 km (23%) | ~5.9 km | ~AU$260 |
| Selwyn | 10 | 9 km (90%) | 0 km (0%) | 1 km (10%) | ~0.8 km | ~AU$135 |

Price order (high → low): **Perisher > Thredbo > Selwyn** — confirmed across
sources. Exact figures vary by purchase method (window vs online-advance), so
shown as "roughly"; the order is what matters.
Longest-run order: **Thredbo > Perisher > Selwyn**.

## Metric notes & open items

- **Size ("how big"):** **total slope length (km)** — confirmed. (Skiable area in
  hectares isn't published consistently for AU resorts; slope km is uniform and a
  fair size proxy.)
- **Ability level:** difficulty split above is directly usable (proportion of
  terrain by easy/intermediate/advanced). ✅
- **Run length:** metric = **longest run** (replacing average run length, which
  couldn't be sourced cleanly) — confirmed kept. Data found for all three;
  approximate/mixed-source but the order is unambiguous.
- **Price:** verified — shown as **"roughly $X"**. Exact prices vary by purchase
  method; the **order** (Perisher > Thredbo > Selwyn) is
  confirmed and is what matters.

## Cross-reference
- Lift-served elevations & mid-mountain figures: see [CLAUDE.md](CLAUDE.md) /
  [FACTORS.md](FACTORS.md).
- Live open-lift % and base depth: OnTheSnow, not static — see [FACTORS.md](FACTORS.md).
