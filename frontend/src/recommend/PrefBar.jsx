import { prettyRange } from '../lib/dates.js'
import styles from './PrefBar.module.css'

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1)

// The chips summarising the user's picks — dates first, then ability, then any opt-ins.
function prefChips(prefs, range) {
  const chips = []
  if (range && range.start) chips.push(`📅 ${prettyRange(range)}`)
  chips.push(`${cap(prefs.ability)} skier`)
  if (prefs.cost_matters) chips.push('💲 cost matters')
  if (prefs.bigger_resort) chips.push('🗺️ bigger resort')
  if (prefs.longer_runs) chips.push('↔️ longer runs')
  if (prefs.snow_pref === 'snowy') chips.push('❄️ fresh snow')
  else if (prefs.snow_pref === 'bluebird') chips.push('☀️ bluebird')
  return chips
}

// Persistent summary of the user's picks, with an Edit button that reopens the wizard
// pre-filled. Sits at the top of the Recommendation view once prefs are set.
export default function PrefBar({ prefs, range, onEdit }) {
  return (
    <div className={styles.prefbar}>
      <span className={styles.lead}>Your picks</span>
      <div className={styles.pchips}>
        {prefChips(prefs, range).map((c) => (
          <span key={c} className={styles.pchip}>{c}</span>
        ))}
      </div>
      <button type="button" className={styles.editBtn} onClick={onEdit}>
        ✎ Edit
      </button>
    </div>
  )
}
