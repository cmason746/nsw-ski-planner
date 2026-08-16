// API client — thin wrappers over the deployed HTTP API (see CLAUDE.md → Deployment).
// Base URL is overridable via VITE_API_BASE (e.g. for a future staging stack); it
// falls back to the live prod stack so the app works with no env setup.
const API_BASE =
  import.meta.env.VITE_API_BASE ||
  'https://ayyfk7jzlb.execute-api.ap-southeast-2.amazonaws.com'

// GET /conditions → the neutral overview, keyed by resort_key. 503 until the ingest
// Lambda has populated the cache (schedule runs every 3h).
export async function getConditions() {
  const res = await fetch(`${API_BASE}/conditions`)
  if (!res.ok) {
    // 503 = the ingest Lambda hasn't populated the cache yet (runs every 3h).
    const msg =
      res.status === 503
        ? 'Conditions aren’t ready yet — the data refresh hasn’t run. Try again shortly.'
        : `Request failed (${res.status}).`
    throw new Error(msg)
  }
  return res.json()
}

// POST /recommend → ranked cards (up to 3). Body: the wizard's prefs plus the
// selected dates (both required; selected_dates must be non-empty).
export async function postRecommend(prefs, selectedDates) {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...prefs, selected_dates: selectedDates }),
  })
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}).`)
  }
  return res.json()
}
