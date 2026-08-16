import { factorCell } from '../lib/overviewFormat.js'
import Icon from '../lib/Icon.jsx'
import styles from './DayCard.module.css'

// One factor's cell inside the AM/PM grid. Both columns render the same day-level
// factor order, so a non-snowing half may be asked for a snow figure it lacks — that
// comes back muted ("0cm = no new snow" / "–") to keep the two columns' rows level.
// A factor that genuinely doesn't apply (and isn't a fillable snow gap) renders empty
// so the grid column stays balanced. `hidden` collapses the row until the card expands.
export default function FactorCell({ factorKey, win, side, hidden }) {
  const cls = `${styles.wcell} ${styles[side.toLowerCase()]} ${styles.fcell} ${hidden ? styles.hidden : ''}`
  const parts = factorCell(factorKey, win, side)

  if (!parts) return <div className={cls} />

  return (
    <div className={cls}>
      <div className={`${styles.factor} ${parts.muted ? styles.muted : ''}`}>
        <span className={styles.ico}><Icon name={parts.ico} color={parts.color} size={14} /></span>
        <span className={styles.val}>{parts.val}</span>
        {parts.lab ? <span className={styles.eq}>=</span> : null}
        <span className={styles.lab}>{parts.lab}</span>
      </div>
    </div>
  )
}
