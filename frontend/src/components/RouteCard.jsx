import { LEVELS, levelInfo } from '../lib/risk.js'
import { fmtDuration, fmtMiles, fmtTime } from '../lib/format.js'

function RiskBar({ route }) {
  const total = route.distance_mi || 1
  const parts = route.miles_by_level.map((mi, i) => ({ mi, ...LEVELS[i] }))
  if (route.unknown_miles) parts.push({ mi: route.unknown_miles, name: 'Unknown', color: '#cbd5e1' })
  return (
    <div className="riskbar" role="img" aria-label={parts.filter((p) => p.mi > 0).map((p) => `${p.name} ${Math.round(p.mi)} miles`).join(', ')}>
      {parts.map((p) =>
        p.mi > 0 ? <span key={p.name} style={{ width: `${(p.mi / total) * 100}%`, background: p.color }} title={`${p.name}: ${Math.round(p.mi)} mi`} /> : null,
      )}
    </div>
  )
}

export default function RouteCard({ route, selected, onSelect }) {
  const [, , high, severe, noTravel] = route.miles_by_level
  const worst = levelInfo(route.max_level)
  return (
    <button type="button" className={`route-card ${selected ? 'selected' : ''}`} onClick={onSelect} aria-pressed={selected}>
      <div className="rc-head">
        <span className="dot" style={{ background: route.color }} />
        <strong>{route.name}</strong>
        {route.recommended && <span className="badge rec">★ Recommended</span>}
        {route.tags.map((t) => (
          <span key={t} className="badge">{t}</span>
        ))}
      </div>
      <div className="rc-stats">
        <div><span>Distance</span>{fmtMiles(route.distance_mi)}</div>
        <div><span>Driving</span>{fmtDuration(route.drive_hours)}</div>
        <div><span>Door to door</span>{fmtDuration(route.total_hours)}</div>
        <div><span>Arrives</span>{fmtTime(route.arrival)}</div>
      </div>
      <RiskBar route={route} />
      <div className="rc-risk">
        <span className="pill" style={{ background: worst.color }}>Worst: {worst.name}</span>
        <span>No Travel <b>{Math.round(noTravel)}</b> mi</span>
        <span>Severe <b>{Math.round(severe)}</b> mi</span>
        <span>High <b>{Math.round(high)}</b> mi</span>
        <span>Avg risk <b>{route.avg_risk == null ? '–' : route.avg_risk.toFixed(2)}</b></span>
      </div>
    </button>
  )
}
