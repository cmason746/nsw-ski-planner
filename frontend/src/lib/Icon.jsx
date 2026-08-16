import { ICONS } from './iconMap.js'

// One icon. `name` keys into ICONS (see iconMap.js); `color` overrides the default
// (used for temperature bands). Renders nothing for an unknown name (e.g. a factor
// with no icon).
export default function Icon({ name, color, size = 15 }) {
  const entry = ICONS[name]
  if (!entry) return null
  const [Comp, defaultColor] = entry
  return <Comp size={size} color={color ?? defaultColor} strokeWidth={2.25} />
}
