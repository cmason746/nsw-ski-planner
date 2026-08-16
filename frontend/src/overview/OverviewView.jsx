import { useState } from 'react'
import ResortSection from './ResortSection.jsx'
import DatePicker from '../components/DatePicker.jsx'
import { prettyRange, rangeList } from '../lib/dates.js'
import styles from './OverviewView.module.css'

// Stable display order (the API returns an unordered dict keyed by resort_key).
const RESORT_ORDER = ['perisher', 'thredbo', 'selwyn']

function orderResorts(conditions) {
  const keys = Object.keys(conditions)
  const known = RESORT_ORDER.filter((k) => k in conditions)
  const rest = keys.filter((k) => !RESORT_ORDER.includes(k))
  return [...known, ...rest]
}

// Neutral, preference-independent conditions view — three resort bands stacked
// vertically, driven by GET /conditions and filtered to the selected date range.
export default function OverviewView({ conditions, loading, error, range, availableDates, onChangeRange }) {
  const [pickerOpen, setPickerOpen] = useState(false)

  if (loading) {
    return <div className={styles.state}>Loading conditions…</div>
  }
  if (error) {
    return (
      <div className={styles.state}>
        <p className={styles.stateHead}>Couldn’t load conditions</p>
        <p className={styles.stateSub}>{error}</p>
      </div>
    )
  }
  if (!conditions) return null

  const keys = orderResorts(conditions)
  const selected = range ? new Set(rangeList(range.start, range.end)) : null

  // Filter each resort's days to the selected range (fall back to all days if no range).
  const filtered = (resort) => ({
    ...resort,
    days: selected ? resort.days.filter((d) => selected.has(d.date)) : resort.days,
  })

  return (
    <section className={styles.view}>
      <div className={styles.daterow}>
        <span className={styles.lead}>Showing conditions for</span>
        <div className={styles.pickerWrap}>
          <button
            type="button"
            className={styles.datepick}
            onClick={() => setPickerOpen((o) => !o)}
          >
            <span className={styles.cal}>📅</span>
            <span>{prettyRange(range)}</span>
            <span className={styles.caret}>▾</span>
          </button>
          {pickerOpen ? (
            <>
              <div className={styles.backdrop} onClick={() => setPickerOpen(false)} />
              <div className={styles.popover}>
                <DatePicker availableDates={availableDates} range={range} onChange={onChangeRange} />
              </div>
            </>
          ) : null}
        </div>
      </div>

      {keys.map((key) => (
        <ResortSection key={key} resort={filtered(conditions[key])} />
      ))}
    </section>
  )
}
