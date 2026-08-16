import { useState, useEffect, useMemo } from 'react'
import TopBar from './components/TopBar'
import OverviewView from './overview/OverviewView'
import RecommendationView from './recommend/RecommendationView'
import PreferencesWizard from './recommend/PreferencesWizard'
import { getConditions, postRecommend } from './api/client'
import { rangeList } from './lib/dates'
import styles from './App.module.css'

export default function App() {
  // Shared app state lives here so switching tabs never loses it.
  const [activeTab, setActiveTab] = useState('overview') // 'overview' | 'recommend'

  // GET /conditions drives the Overview. Fetched once on mount.
  const [conditions, setConditions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // The Overview's live date selection (also seeds the wizard's date step). Defaults to
  // today + the next 6 days once conditions arrive.
  const [dateRange, setDateRange] = useState(null)

  // Preferences + the resulting recommendation. `recRange` is the date range the current
  // cards were computed for — shown in the pref bar, so it stays honest even if the user
  // later tweaks the Overview dates without re-running.
  const [prefs, setPrefs] = useState(null)
  const [recRange, setRecRange] = useState(null)
  const [recCards, setRecCards] = useState(null)
  const [recLoading, setRecLoading] = useState(false)
  const [recError, setRecError] = useState(null)

  const [wizardOpen, setWizardOpen] = useState(false)

  const hasPrefs = prefs !== null

  // Selectable days = exactly what the API returned (resorts share the same dates).
  // Memoised so its identity is stable across renders (it feeds a useEffect + children).
  const availableDates = useMemo(
    () => (conditions ? (Object.values(conditions)[0]?.days ?? []).map((d) => d.date) : []),
    [conditions],
  )

  useEffect(() => {
    let cancelled = false
    getConditions()
      .then((data) => {
        if (!cancelled) setConditions(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Once conditions load, default the selection to today + the next 6 days (the upcoming
  // week), clamped to what's actually available.
  useEffect(() => {
    if (conditions && !dateRange && availableDates.length > 0) {
      const endIdx = Math.min(6, availableDates.length - 1)
      setDateRange({ start: availableDates[0], end: availableDates[endIdx] })
    }
  }, [conditions, dateRange, availableDates])

  async function runRecommend(nextPrefs, range) {
    setRecLoading(true)
    setRecError(null)
    try {
      const cards = await postRecommend(nextPrefs, rangeList(range.start, range.end))
      setRecCards(cards)
    } catch (err) {
      setRecError(err.message)
      setRecCards(null)
    } finally {
      setRecLoading(false)
    }
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    // First switch to Recommendation with no prefs yet → open the wizard (nothing to
    // show there until prefs exist). Once set, revisiting just shows the saved result.
    if (tab === 'recommend' && !hasPrefs) setWizardOpen(true)
  }

  // Wizard finished: commit prefs + dates, mirror the dates back to the Overview
  // selection, jump to the Recommendation, and fetch it.
  const handleWizardComplete = (nextPrefs, nextRange) => {
    setPrefs(nextPrefs)
    setDateRange(nextRange)
    setRecRange(nextRange)
    setWizardOpen(false)
    setActiveTab('recommend')
    runRecommend(nextPrefs, nextRange)
  }

  return (
    <div className={styles.wrap}>
      <TopBar activeTab={activeTab} onTabChange={handleTabChange} onOpenPrefs={() => setWizardOpen(true)} />

      {/* Both views stay mounted; the inactive one is hidden (not unmounted) so scroll
          position and expanded cards survive tab switches. */}
      <div hidden={activeTab !== 'overview'}>
        <OverviewView
          conditions={conditions}
          loading={loading}
          error={error}
          range={dateRange}
          availableDates={availableDates}
          onChangeRange={setDateRange}
        />
      </div>
      <div hidden={activeTab !== 'recommend'}>
        <RecommendationView
          prefs={prefs}
          range={recRange}
          cards={recCards}
          loading={recLoading}
          error={recError}
          onEdit={() => setWizardOpen(true)}
        />
      </div>

      <PreferencesWizard
        open={wizardOpen}
        availableDates={availableDates}
        initialPrefs={prefs}
        initialRange={dateRange}
        onComplete={handleWizardComplete}
        onClose={() => setWizardOpen(false)}
      />
    </div>
  )
}
