import { useState } from 'react'
import { ORDER, DEFAULT_ROWS, dayType } from '../lib/overviewFormat.js'
import { dayParts } from '../lib/dates.js'
import Icon from '../lib/Icon.jsx'
import FactorCell from './FactorCell.jsx'
import styles from './DayCard.module.css'

// One picked day for one resort. Top to bottom: date header → recent_snow line (per-day)
// → AM/PM 2-column grid → "+ more" expand. The whole day shares one factor order (the
// "snowiest" of its two windows) so AM and PM rows line up.
export default function DayCard({ day }) {
  const [open, setOpen] = useState(false)
  const order = ORDER[dayType(day.am, day.pm)]
  const extra = Math.max(order.length - DEFAULT_ROWS, 0)
  const { dow, num } = dayParts(day.date)

  return (
    <div className={styles.card}>
      <div className={styles.cardDate}>
        <span className={styles.dow}>{dow}</span>
        <span className={styles.num}>{num}</span>
      </div>

      <div className={styles.recent}>
        <span className={styles.ico}><Icon name="recent" size={15} /></span>
        <span>
          <b>{day.recent_snow.cm}cm</b> – {day.recent_snow.label} in the past 2 days
        </span>
      </div>

      {/* AM/PM as one 2-column grid so each factor slot shares a row across the two
          columns — rows stay level even when a label wraps. */}
      <div className={styles.windows}>
        <div className={`${styles.wcell} ${styles.am} ${styles.wlabel}`}>AM</div>
        <div className={`${styles.wcell} ${styles.pm} ${styles.wlabel}`}>PM</div>

        <RsCell win={day.am} side="am" />
        <RsCell win={day.pm} side="pm" />

        {order.map((key, i) => {
          const hidden = i >= DEFAULT_ROWS && !open
          return (
            <FactorCellPair key={key} factorKey={key} day={day} hidden={hidden} />
          )
        })}
      </div>

      {extra > 0 ? (
        <button type="button" className={styles.expand} onClick={() => setOpen((o) => !o)}>
          {open ? '− less' : `+ more (${extra})`}
        </button>
      ) : null}
    </div>
  )
}

// rain_snow header for one window — always at the top of its column, coloured by type.
function RsCell({ win, side }) {
  return (
    <div className={`${styles.wcell} ${styles[side]} ${styles.rscell}`}>
      <div className={`${styles.rs} ${styles[win.type]}`}>
        <span className={styles.ico}><Icon name={`cond-${win.type}`} size={18} /></span>
        <span className={styles.txt}>{win.rain_snow}</span>
      </div>
    </div>
  )
}

// AM + PM cells for one factor row, emitted adjacently so the CSS grid pairs them.
function FactorCellPair({ factorKey, day, hidden }) {
  return (
    <>
      <FactorCell factorKey={factorKey} win={day.am} side="AM" hidden={hidden} />
      <FactorCell factorKey={factorKey} win={day.pm} side="PM" hidden={hidden} />
    </>
  )
}
