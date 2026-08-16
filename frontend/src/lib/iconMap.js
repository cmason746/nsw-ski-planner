import {
  Sun, CloudSun, Cloud, CloudSnow, CloudHail, CloudRain, Snowflake,
  Wind, Droplets, MountainSnow, Thermometer, Layers, CableCar, Gauge,
  Map as MapIcon, MoveHorizontal, DollarSign,
} from 'lucide-react'

// The whole app's icon set + colours in one place (replaces the emoji placeholders).
// Each entry is [Lucide component, default colour]. Colours are semantic: the weather
// icons reuse the card's rain/snow colour language (snow blue, mix purple, rain slate,
// sun amber) so the icon reinforces the header; logistics factors get distinct hues.
export const ICONS = {
  // conditions (rain_snow window type)
  'cond-snow': [CloudSnow, '#2563eb'],
  'cond-mix': [CloudHail, '#7a5cc0'],
  'cond-rain': [CloudRain, '#64748b'],
  'cond-dry': [Sun, '#e0940f'],
  // sunniness by band
  'sun-sunny': [Sun, '#e0940f'],
  'sun-partly': [CloudSun, '#94a3b8'],
  'sun-cloudy': [Cloud, '#94a3b8'],
  // per-window weather factors
  wind: [Wind, '#0d9488'],
  precip: [Droplets, '#3b82f6'],
  amount: [MountainSnow, '#2563eb'],
  quality: [Snowflake, '#2563eb'],
  recent: [CloudSnow, '#2563eb'],
  temperature: [Thermometer, '#e0940f'], // colour usually overridden per band (see tempColor)
  // recommendation-only factors
  conditions: [CloudSun, '#64748b'], // rain_penalty summary
  base_depth: [Layers, '#6366f1'],
  lifts: [CableCar, '#16a34a'],
  ability: [Gauge, '#f4b93e'],
  size: [MapIcon, '#0d9488'],
  run_length: [MoveHorizontal, '#8b5cf6'],
  price: [DollarSign, '#16a34a'],
}

// Sunniness percentage → which sun icon to show.
export function sunIconName(pct) {
  if (pct > 70) return 'sun-sunny'
  if (pct >= 40) return 'sun-partly'
  return 'sun-cloudy'
}

// Temperature → icon colour (icon stays the thermometer). Bands mirror _temperature_field:
// cold <0 (blue), pleasant 0–2 (green), warm 3–6 (amber), hot >6 (red).
export function tempColor(tempC) {
  if (tempC < 0) return '#2563eb'
  if (tempC < 3) return '#16a34a'
  if (tempC <= 6) return '#e0940f'
  return '#dc2626'
}

// Recommendation card factor name → icon name.
export function factorIconName(factor) {
  switch (factor) {
    case 'rain_penalty': return 'conditions'
    case 'sunniness': return 'sun-sunny'
    case 'snow_amount': return 'amount'
    case 'snow_quality': return 'quality'
    case 'wind': return 'wind'
    case 'recent_snow': return 'recent'
    case 'base_depth': return 'base_depth'
    case 'lifts': return 'lifts'
    case 'ability': return 'ability'
    case 'size': return 'size'
    case 'run_length': return 'run_length'
    case 'price': return 'price'
    default: return null
  }
}
