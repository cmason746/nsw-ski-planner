// Recommendation display logic — turns one card's `facts` (same band words as the
// overview, weight-ordered) into "VALUE = descriptor" rows and compact headline chips.
// Lifted from mockups/recommendation.html. NOTE: the real API's rain factor is named
// `rain_penalty` (the mockup used `rain_snow`); handled here. Icons live in Icon.jsx.

// Split a factor value object into its number + unit.
function numUnit(v) {
  if ('kmh' in v) return { n: v.kmh, u: 'km/h' }
  if ('cm' in v) return { n: v.cm, u: 'cm' }
  if ('sunniness_pct' in v) return { n: v.sunniness_pct, u: '% sun' }
  if ('temp_c' in v) return { n: v.temp_c, u: '°C' }
  return { n: '', u: '' }
}

// Long rain/snow phrase → short word for a chip.
function shortRS(s) {
  if (s.startsWith('snow up high')) return 'snow up high'
  if (s.startsWith('snow across')) return 'snowing'
  if (s.startsWith('rain across')) return 'raining'
  if (s.startsWith('no precip')) return 'dry'
  return s
}

// One fact → { val, lab } for a "VALUE = descriptor" row. Same-band AM/PM collapse to
// one descriptor with the two numbers slashed ("82/74% sun = sunny") so rows stay short.
export function factValLab(f) {
  if ('am' in f || 'pm' in f) {
    const a = f.am
    const p = f.pm
    if (typeof a === 'string' || typeof p === 'string') {
      const A = a ? shortRS(a) : ''
      const P = p ? shortRS(p) : ''
      return { lab: !a || !p ? A || P : A === P ? A : `${A} AM · ${P} PM` }
    }
    if (a && p) {
      const ua = numUnit(a)
      const up = numUnit(p)
      if (a.label === p.label) return { val: `${ua.n}, ${up.n}${ua.u}`, lab: a.label }
      return { lab: `${ua.n}${ua.u} ${a.label} AM · ${up.n}${up.u} ${p.label} PM` }
    }
    const v = a || p
    const uv = numUnit(v)
    return { val: `${uv.n}${uv.u}`, lab: v.label }
  }
  if (f.factor === 'recent_snow') return { val: `${f.cm}cm`, lab: f.label }
  if (f.factor === 'lifts') return { lab: `${f.open} of ${f.total} lifts open` }
  if (f.factor === 'base_depth') return { val: `${f.cm}cm`, lab: f.label }
  if (f.factor === 'ability') return { lab: f.label.includes('resort') ? f.label : `resort ${f.label}` }
  return { lab: f.label } // size / run_length / price
}

// Compact headline chip text — band word only (no AM/PM, minimal numbers).
export function chipText(f) {
  if ('am' in f || 'pm' in f) {
    const v = f.am ?? f.pm
    if (typeof v === 'string') return shortRS(v)
    if (f.factor === 'snow_amount') return `${v.cm}cm new snow`
    return v.label
  }
  if (f.factor === 'recent_snow') return `${f.cm}cm recent snow`
  if (f.factor === 'lifts') return `${f.pct}% lifts`
  if (f.factor === 'base_depth') return `${f.cm}cm base`
  return f.label
}
