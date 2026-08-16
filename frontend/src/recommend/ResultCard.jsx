import { useState } from 'react'
import { factValLab, chipText } from '../lib/recommendFormat.js'
import Icon from '../lib/Icon.jsx'
import { factorIconName } from '../lib/iconMap.js'
import { prettyDateLong } from '../lib/dates.js'
import styles from './ResultCard.module.css'

// One ranked result — the best resort for a given day. Collapsed: rank + resort + day
// + top-3 factor chips + score. Expanded: the Bedrock "why" paragraph plus the full
// 8-factor grid (same band words as the Overview). The #1 card is the styled "Top pick"
// and opens expanded by default.
export default function ResultCard({ card, rank }) {
  const [open, setOpen] = useState(rank === 1)
  const headChips = card.facts.slice(0, 3)
  const score = Math.round(card.day_score * 100)

  return (
    <div className={`${styles.rcard} ${rank === 1 ? styles.rank1 : ''} ${open ? styles.open : ''}`}>
      <div className={styles.rhead} onClick={() => setOpen((o) => !o)}>
        <div className={styles.rank}>{rank}</div>

        <div className={styles.rtitle}>
          <div className={styles.top}>
            <span className={styles.resort}>{card.resort}</span>
            <span className={styles.rdate}>{prettyDateLong(card.date)}</span>
            {rank === 1 ? <span className={styles.rwinner}>Top pick</span> : null}
          </div>
          <div className={styles.chips}>
            {headChips.map((f) => (
              <span key={f.factor} className={styles.chip}>
                <span className={styles.ico}><Icon name={factorIconName(f.factor)} size={13} /></span>
                {chipText(f)}
              </span>
            ))}
          </div>
        </div>

        <div className={styles.score} title="Score according to our ski-conditions model">
          <div className={styles.scoreNum}>
            {score}
            <span className={styles.of}>/100</span>
          </div>
          <div className={styles.scoreCap}>our ski-conditions model score</div>
        </div>

        <div className={styles.caret}>⌄</div>
      </div>

      <div className={styles.rbody}>
        <div className={styles.why}>
          <div className={styles.whyLabel}>Why {card.resort} this day</div>
          {card.why}
        </div>
        <div className={styles.factsLabel}>The conditions</div>
        <div className={styles.facts}>
          {card.facts.map((f) => {
            const { val, lab } = factValLab(f)
            return (
              <div key={f.factor} className={styles.frow}>
                <span className={styles.ico}><Icon name={factorIconName(f.factor)} size={14} /></span>
                {val ? (
                  <>
                    <span className={styles.val}>{val}</span>
                    <span className={styles.eq}>=</span>
                  </>
                ) : null}
                <span className={styles.lab}>{lab}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
