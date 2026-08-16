// Overview display logic — the factor ordering + "VALUE = descriptor" building that
// turns one API window into rendered rows. Lifted straight from mockups/overview.html
// (the visual reference), kept here so the components stay declarative.
import { sunIconName, tempColor } from './iconMap.js'

// Factor render order per window type (Charlotte's priority for each condition).
export const ORDER = {
  snow: ['snow_amount', 'snow_quality', 'wind', 'sunniness', 'precip_probability'],
  mix: ['snow_amount', 'wind', 'sunniness', 'snow_quality', 'precip_probability'],
  // Dry/rain windows carry no snow to grade, so they show a plain `temperature` (mid-
  // mountain window average) instead of snow_quality. Dry also carries no
  // precip_probability (backend omits it — a "chance of precip" figure contradicts "no
  // precipitation forecast" when the forecast amount is ~0).
  dry: ['sunniness', 'wind', 'temperature'],
  rain: ['precip_probability', 'wind', 'temperature', 'sunniness'],
}

// "Snowiest wins": AM and PM can differ, but the day picks ONE order so both columns'
// rows line up by factor. Higher rank wins: snow > mix > rain > dry.
const TYPE_RANK = { snow: 4, mix: 3, rain: 2, dry: 1 }
export function dayType(am, pm) {
  return TYPE_RANK[am.type] >= TYPE_RANK[pm.type] ? am.type : pm.type
}

// How many factor rows are shown by default before the "+ more" expand.
export const DEFAULT_ROWS = 2

// snow_amount phrasing names the window (AM/PM) so it reads as this half-day's total,
// never base or recent snow.
const AMOUNT_PHRASE = {
  dusting: (side) => `dusting of snow during the ${side}`,
  decent: (side) => `decent ${side} snow total`,
  dump: (side) => `snow dump during the ${side}`,
}

// One factor → { ico, val, lab, color? } for a "VALUE = descriptor" row. `ico` is an
// icon name (see Icon.jsx); `color` overrides the icon's default (temperature bands).
// `side` is "AM"/"PM". Returns null when the window has no such factor.
export function factorParts(key, win, side) {
  switch (key) {
    case 'snow_amount': {
      const a = win.snow_amount
      if (!a) return null
      const phrase = (AMOUNT_PHRASE[a.label] || (() => a.label))(side)
      return { ico: 'amount', val: `${a.cm}cm`, lab: phrase + (a.note ? ` · ${a.note}` : '') }
    }
    case 'snow_quality': {
      const q = win.snow_quality
      if (!q) return null
      return { ico: 'quality', val: `${q.temp_c}°C`, lab: q.label }
    }
    case 'temperature': {
      const t = win.temperature
      if (!t) return null // only present on dry/rain windows
      return { ico: 'temperature', color: tempColor(t.temp_c), val: `${t.temp_c}°C`, lab: t.label }
    }
    case 'wind':
      return { ico: 'wind', val: `${win.wind.kmh}km/h`, lab: win.wind.label }
    case 'sunniness': {
      const s = win.sunniness
      return { ico: sunIconName(s.sunniness_pct), val: `${s.sunniness_pct}% sun`, lab: s.label }
    }
    case 'precip_probability': {
      const p = win.precip_probability
      if (!p) return null // dry windows carry no precip_probability (e.g. a dry half of a snowy day)
      return { ico: 'precip', val: `${p.pct}%`, lab: `${p.label} chance of precipitation` }
    }
    default:
      return null
  }
}

// Both columns use the day order, so a non-snowing half may be asked for a snow figure
// it lacks. Fill those muted rather than leave a gap, so rows stay level across AM/PM.
export function factorCell(key, win, side) {
  const parts = factorParts(key, win, side)
  if (parts) return parts
  if (key === 'snow_amount') return { ico: 'amount', val: '0cm', lab: 'no new snow', muted: true }
  if (key === 'snow_quality') return { ico: 'quality', val: '–', lab: '', muted: true }
  return null // factor doesn't apply to this window and isn't a fillable snow gap
}
