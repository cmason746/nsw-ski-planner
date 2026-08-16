import { useState, useEffect } from 'react'
import DatePicker from '../components/DatePicker.jsx'
import { prettyRange } from '../lib/dates.js'
import styles from './PreferencesWizard.module.css'

// One-question-at-a-time modal. The first step is the date range (pre-filled from the
// shared selection so the user confirms rather than re-picks); then ability, cost, and —
// for non-beginners only — size, runs, and snow preference. "Don't mind" is always a
// valid answer, but every question must be answered before Next enables.
const QUESTIONS = [
  { key: 'dates', type: 'dates', q: 'When are you thinking of skiing?' },
  {
    key: 'ability',
    q: 'What level skier are you?',
    opts: [
      { v: 'beginner', l: 'Beginner' },
      { v: 'intermediate', l: 'Intermediate' },
      { v: 'advanced', l: 'Advanced' },
    ],
  },
  {
    key: 'cost_matters',
    q: 'Is lift-ticket cost important to you?',
    opts: [
      { v: true, l: 'Yes — keep it cheap', i: '💲' },
      { v: false, l: "Don't mind" },
    ],
  },
  {
    key: 'bigger_resort',
    adv: true,
    q: 'Want a bigger resort with more terrain?',
    opts: [
      { v: true, l: 'Yes — bigger is better', i: '🗺️' },
      { v: false, l: "Don't mind" },
    ],
  },
  {
    key: 'longer_runs',
    adv: true,
    q: 'Do you like longer runs?',
    opts: [
      { v: true, l: 'Yes — the longer the better', i: '↔️' },
      { v: false, l: "Don't mind" },
    ],
  },
  {
    key: 'snow_pref',
    adv: true,
    q: 'Fresh snow or bluebird days?',
    opts: [
      { v: 'snowy', l: 'Fresh snow', i: '❄️' },
      { v: 'bluebird', l: 'Bluebird (sunny)', i: '☀️' },
      { v: 'dont_mind', l: "Don't mind" },
    ],
  },
]

export default function PreferencesWizard({
  open,
  availableDates,
  initialPrefs,
  initialRange,
  onComplete,
  onClose,
}) {
  const [draft, setDraft] = useState({})
  const [step, setStep] = useState(0)

  // Re-seed the draft whenever the modal opens (fresh, or pre-filled for an Edit).
  useEffect(() => {
    if (!open) return
    setDraft({ ...(initialPrefs || {}), dates: initialRange || null })
    setStep(0)
  }, [open, initialPrefs, initialRange])

  if (!open) return null

  const beginner = draft.ability === 'beginner'
  const path = QUESTIONS.filter((q) => !(q.adv && beginner))
  const q = path[step]
  const isLast = step === path.length - 1

  const answered =
    q.type === 'dates' ? !!(draft.dates && draft.dates.start) : draft[q.key] !== undefined

  function pick(value) {
    setDraft((d) => ({ ...d, [q.key]: value }))
  }

  function next() {
    if (!isLast) {
      setStep((s) => s + 1)
      return
    }
    // Finish — beginners drop the advanced answers entirely.
    const prefs = { ability: draft.ability, cost_matters: !!draft.cost_matters }
    if (draft.ability !== 'beginner') {
      prefs.bigger_resort = !!draft.bigger_resort
      prefs.longer_runs = !!draft.longer_runs
      prefs.snow_pref = draft.snow_pref
    }
    onComplete(prefs, draft.dates)
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.modalTop}>
          <div className={styles.dots}>
            {path.map((_, i) => (
              <div
                key={i}
                className={`${styles.dot} ${i < step ? styles.done : ''} ${i === step ? styles.current : ''}`}
              />
            ))}
          </div>
          <div className={styles.topRight}>
            <span className={styles.stepCount}>
              {step + 1} of {path.length}
            </span>
            <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>
        </div>

        {step === 0 ? (
          <div className={styles.intro}>Tell us what matters — we'll rank the resorts for you.</div>
        ) : null}

        <div className={styles.q}>{q.q}</div>

        {q.type === 'dates' ? (
          <div className={styles.dateStep}>
            <DatePicker
              availableDates={availableDates}
              range={draft.dates}
              onChange={(r) => setDraft((d) => ({ ...d, dates: r }))}
            />
            <div className={styles.dateSummary}>
              {draft.dates && draft.dates.start ? prettyRange(draft.dates) : 'Pick a start and end day'}
            </div>
          </div>
        ) : (
          <div className={styles.opts}>
            {q.opts.map((o) => (
              <button
                key={String(o.v)}
                type="button"
                className={`${styles.opt} ${draft[q.key] === o.v ? styles.sel : ''}`}
                onClick={() => pick(o.v)}
              >
                {o.i ? <span className={styles.oico}>{o.i}</span> : null}
                <span>{o.l}</span>
              </button>
            ))}
          </div>
        )}

        <div className={styles.modalNav}>
          <button
            type="button"
            className={styles.backBtn}
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
          >
            ← Back
          </button>
          <button type="button" className={styles.nextBtn} disabled={!answered} onClick={next}>
            {isLast ? 'See recommendations →' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  )
}
