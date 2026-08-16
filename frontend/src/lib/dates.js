// Date helpers. The API returns ISO date strings ("2026-08-15"); the UI wants a
// weekday + day-of-month split for day-card headers, a compact range for the
// date-picker pill, a long form for result cards, plus small range utilities.
// Everything is parsed at local midnight so the weekday never drifts by a day.

function parseISO(iso) {
  return new Date(iso + 'T00:00:00')
}

function toISO(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// "2026-08-15" → { dow: "Thu", num: "15" } for the day-card header.
export function dayParts(iso) {
  const d = parseISO(iso)
  return {
    dow: d.toLocaleDateString('en-AU', { weekday: 'short' }),
    num: d.toLocaleDateString('en-AU', { day: 'numeric' }),
  }
}

// "2026-08-15" → "Saturday, 15 Aug" for the recommendation card header.
export function prettyDateLong(iso) {
  return parseISO(iso).toLocaleDateString('en-AU', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  })
}

// { start, end } ISO → "Thu 13 – Mon 17 Aug" for the date-picker pill.
export function prettyRange(range) {
  if (!range || !range.start) return ''
  const first = parseISO(range.start)
  const last = parseISO(range.end || range.start)
  const dm = (d) => d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric' })
  const month = last.toLocaleDateString('en-AU', { month: 'short' })
  if (range.start === range.end || !range.end) return `${dm(first)} ${month}`
  return `${dm(first)} – ${dm(last)} ${month}`
}

// ISO + n days → ISO.
export function addDays(iso, n) {
  const d = parseISO(iso)
  d.setDate(d.getDate() + n)
  return toISO(d)
}

// Inclusive list of ISO dates from start to end — what POST /recommend wants as
// selected_dates, and what the Overview filters its day-cards to.
export function rangeList(start, end) {
  if (!start) return []
  const out = []
  let cur = start
  const stop = end || start
  while (cur <= stop) {
    out.push(cur)
    cur = addDays(cur, 1)
  }
  return out
}

export { toISO, parseISO }
