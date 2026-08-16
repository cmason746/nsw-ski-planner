import { useState } from 'react'
import { parseISO, toISO } from '../lib/dates.js'
import styles from './DatePicker.module.css'

// Shared range calendar, used inline in the wizard and inside the Overview's pill
// popover. Selectable days are exactly the dates the API returned (`availableDates`);
// anything outside that window is disabled, so we can never select a day with no data.
//
// Range selection is two clicks: first sets the anchor (a 1-day range), second sets the
// other end (min/max sorted). A third click starts a new range.
//
// Props: availableDates (sorted ISO[]), range ({start,end}), onChange({start,end}).
export default function DatePicker({ availableDates, range, onChange }) {
  const [anchor, setAnchor] = useState(null)

  if (!availableDates || availableDates.length === 0) return null

  const available = new Set(availableDates)
  const weeks = buildWeeks(availableDates)

  function handleClick(iso) {
    if (!available.has(iso)) return
    if (anchor === null) {
      setAnchor(iso)
      onChange({ start: iso, end: iso })
    } else {
      const start = anchor < iso ? anchor : iso
      const end = anchor < iso ? iso : anchor
      setAnchor(null)
      onChange({ start, end })
    }
  }

  const inRange = (iso) => range && range.start && iso >= range.start && iso <= (range.end || range.start)

  return (
    <div className={styles.picker}>
      <div className={styles.monthLabel}>{monthLabel(availableDates)}</div>
      <div className={styles.grid}>
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
          <div key={d} className={styles.dow}>{d}</div>
        ))}
        {weeks.flat().map((cell) => {
          if (cell === null) return <div key={Math.random()} className={styles.empty} />
          const selectable = available.has(cell.iso)
          const selected = inRange(cell.iso)
          const isStart = range && cell.iso === range.start
          const isEnd = range && cell.iso === (range.end || range.start)
          const cls = [
            styles.day,
            !selectable ? styles.disabled : '',
            selected ? styles.selected : '',
            isStart ? styles.start : '',
            isEnd ? styles.end : '',
          ].join(' ')
          return (
            <button
              key={cell.iso}
              type="button"
              className={cls}
              disabled={!selectable}
              onClick={() => handleClick(cell.iso)}
            >
              {cell.num}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// Build a Monday-first week matrix covering the whole available window.
function buildWeeks(availableDates) {
  const first = parseISO(availableDates[0])
  const last = parseISO(availableDates[availableDates.length - 1])

  // Back up to the Monday of the first week (getDay: 0=Sun..6=Sat → Mon offset).
  const gridStart = new Date(first)
  const mondayOffset = (first.getDay() + 6) % 7
  gridStart.setDate(first.getDate() - mondayOffset)

  const weeks = []
  let cur = new Date(gridStart)
  while (cur <= last || cur.getDay() !== 1) {
    const week = []
    for (let i = 0; i < 7; i++) {
      week.push({ iso: toISO(cur), num: cur.getDate() })
      cur = new Date(cur)
      cur.setDate(cur.getDate() + 1)
    }
    weeks.push(week)
    if (cur > last && cur.getDay() === 1) break
  }
  return weeks
}

function monthLabel(availableDates) {
  const first = parseISO(availableDates[0])
  const last = parseISO(availableDates[availableDates.length - 1])
  const opts = { month: 'long' }
  const fm = first.toLocaleDateString('en-AU', opts)
  const lm = last.toLocaleDateString('en-AU', opts)
  const year = last.getFullYear()
  return fm === lm ? `${fm} ${year}` : `${fm} – ${lm} ${year}`
}
