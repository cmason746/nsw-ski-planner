import PrefBar from './PrefBar.jsx'
import ResultCard from './ResultCard.jsx'
import styles from './RecommendationView.module.css'

// The ranked result view — a persistent "Your picks" bar, then one card per top day
// (best resort that day), ranked best-first. Driven by POST /recommend.
export default function RecommendationView({ prefs, range, cards, loading, error, onEdit }) {
  // Before the wizard has ever completed there are no prefs — the tab is disabled in
  // that state, so this is just a safety net.
  if (!prefs) {
    return (
      <section className={styles.state}>
        <p>Set your preferences to see a recommendation.</p>
      </section>
    )
  }

  return (
    <section className={styles.view}>
      <PrefBar prefs={prefs} range={range} onEdit={onEdit} />

      {loading ? (
        <div className={styles.state}>Finding the best resorts for your days…</div>
      ) : error ? (
        <div className={styles.state}>
          <p className={styles.stateHead}>Couldn’t load your recommendation</p>
          <p className={styles.stateSub}>{error}</p>
        </div>
      ) : cards && cards.length > 0 ? (
        <>
          <div className={styles.sectionTitle}>
            Best resort for each of your selected days, ordered by score
          </div>
          {cards.map((card, i) => (
            <ResultCard key={card.date + card.resort_key} card={card} rank={i + 1} />
          ))}
        </>
      ) : (
        <div className={styles.state}>No skiable days in your selection.</div>
      )}
    </section>
  )
}
