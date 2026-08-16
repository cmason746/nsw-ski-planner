import { Fragment } from 'react'
import DayCard from './DayCard.jsx'
import styles from './ResortSection.module.css'

// One resort's band: a heading carrying the static, per-day-invariant snapshot
// (open lifts, base depth, elevation range, character words), then a horizontal row
// of day-cards. Many days → the row scrolls sideways, keeping the band compact so all
// three resorts stay visible together.
export default function ResortSection({ resort }) {
  // Build the meta chips, skipping scraped values that are missing (lifts / base depth
  // can be absent from the source — e.g. Selwyn's open-lift count). Omitting the chip
  // entirely reads cleaner than a "–", which looks like "zero open", and matches the
  // recommendation view (which already drops N/A factors). Dots are interleaved after,
  // so there are never dangling separators.
  const chips = []
  if (resort.lifts.pct != null) {
    chips.push(
      <>
        <span className={styles.k}>{resort.lifts.pct}%</span> lifts ({resort.lifts.label})
      </>,
    )
  }
  if (resort.base_depth.cm != null) {
    chips.push(
      <>
        <span className={styles.k}>{resort.base_depth.cm}cm</span> base
      </>,
    )
  }
  chips.push(
    <>
      elevation <span className={styles.k}>{resort.elevations.low}–{resort.elevations.high} m</span>
    </>,
    resort.character[0],
    resort.character[1],
  )

  return (
    <div className={styles.resort}>
      <div className={styles.resortHead}>
        <span className={styles.resortName}>{resort.name}</span>
        <span className={styles.resortMeta}>
          {chips.map((chip, i) => (
            <Fragment key={i}>
              {i > 0 ? <span className={styles.dot}>·</span> : null}
              <span className={styles.chip}>{chip}</span>
            </Fragment>
          ))}
        </span>
      </div>

      <div className={styles.dayRow}>
        {resort.days.map((day) => (
          <DayCard key={day.date} day={day} />
        ))}
      </div>
    </div>
  )
}
