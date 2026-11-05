// Risk levels and the continuous "score" used to paint the heatmap.
// Level thresholds mirror backend/routing/risk.py; the score interpolates
// between them so the heatmap fades smoothly instead of stepping.

export const LEVELS = [
  { name: 'Low', color: '#16a34a' },
  { name: 'Moderate', color: '#ca8a04' },
  { name: 'High', color: '#ea580c' },
  { name: 'Severe', color: '#dc2626' },
  { name: 'No Travel', color: '#7e22ce' },
]
export const UNKNOWN = { name: 'Unknown', color: '#94a3b8' }

export const levelInfo = (level) => (level == null ? UNKNOWN : LEVELS[level])

// value -> score knots (score 1 = Moderate threshold ... 4 = No Travel)
const KNOTS = {
  wind: [[15, 0], [25, 1], [35, 2], [45, 3], [55, 4]],
  rain: [[0.02, 0], [0.1, 1], [0.25, 2], [0.5, 3], [1.0, 4]],
  snow: [[0.1, 0], [0.5, 1], [1.0, 2], [2.0, 3], [3.0, 4]],
}

function interp(v, knots) {
  if (v == null) return null
  if (v <= knots[0][0]) return 0
  for (let i = 1; i < knots.length; i++) {
    const [x1, y1] = knots[i]
    if (v <= x1) {
      const [x0, y0] = knots[i - 1]
      return y0 + ((v - x0) / (x1 - x0)) * (y1 - y0)
    }
  }
  return 4
}

// Wind score including the load rules (heavy trucks: worse in strong wind).
export function windScore(mph, loadLb) {
  const s = interp(mph, KNOTS.wind)
  if (s == null) return null
  if (mph >= 45 && loadLb > 30000) return 4
  if (mph >= 35 && mph < 45 && loadLb > 40000) return Math.max(s, 3)
  return s
}

export function cellScore(variable, wind, rain, snow, loadLb) {
  const w = windScore(wind, loadLb)
  const r = interp(rain, KNOTS.rain)
  const s = interp(snow, KNOTS.snow)
  if (variable === 'wind') return w
  if (variable === 'rain') return r
  if (variable === 'snow') return s
  const vals = [w, r, s].filter((x) => x != null)
  return vals.length ? Math.max(...vals) : null
}

// score (0..4) -> RGBA. Calm weather stays transparent so the map stays readable.
const RAMP = [
  [0.6, [234, 179, 8, 0]],
  [1, [234, 179, 8, 0.38]],
  [2, [249, 115, 22, 0.5]],
  [3, [239, 68, 68, 0.6]],
  [4, [126, 34, 206, 0.68]],
]

export function scoreColor(score) {
  if (score == null || score <= RAMP[0][0]) return [0, 0, 0, 0]
  for (let i = 1; i < RAMP.length; i++) {
    const [x1, c1] = RAMP[i]
    if (score <= x1) {
      const [x0, c0] = RAMP[i - 1]
      const t = (score - x0) / (x1 - x0)
      return c0.map((v, k) => v + (c1[k] - v) * t)
    }
  }
  return RAMP[RAMP.length - 1][1]
}
