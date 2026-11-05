import { useCallback, useMemo, useState } from 'react'
import TripForm from './components/TripForm.jsx'
import RouteCard from './components/RouteCard.jsx'
import CheckpointTable from './components/CheckpointTable.jsx'
import MapView from './components/MapView.jsx'
import HeatControls from './components/HeatControls.jsx'
import { fetchHeatmap, planTrip } from './lib/api.js'
import { renderFrames, truckPosition } from './lib/heatFrames.js'
import { LEVELS } from './lib/risk.js'
import { fmtTimeLong } from './lib/format.js'

const makeCanvas = (w, h) => Object.assign(document.createElement('canvas'), { width: w, height: h })

export default function App() {
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [focus, setFocus] = useState(null)
  const [tab, setTab] = useState('routes')

  const [heat, setHeat] = useState(null)
  const [heatLoading, setHeatLoading] = useState(false)
  const [heatError, setHeatError] = useState(null)
  const [showHeat, setShowHeat] = useState(true)
  const [variable, setVariable] = useState('risk')
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)

  const onSubmit = useCallback(async (payload) => {
    setLoading(true)
    setError(null)
    setHeat(null)
    setHeatError(null)
    setPlaying(false)
    try {
      const p = await planTrip(payload)
      setPlan(p)
      setSelectedId(p.recommendation.route_id)
      setHour(0)
      setTab('routes')
      setHeatLoading(true)
      fetchHeatmap(p.plan_id)
        .then(setHeat)
        .catch((e) => setHeatError(e.message))
        .finally(() => setHeatLoading(false))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // All 49 frames are rendered once per (data, variable, load); the slider only swaps URLs.
  const frames = useMemo(
    () => (heat && plan ? renderFrames(heat, variable, plan.load_lb, makeCanvas) : null),
    [heat, variable, plan],
  )

  const selected = plan?.routes.find((r) => r.id === selectedId)
  const truck = useMemo(
    () => (heat && selected ? truckPosition(selected, Date.parse(heat.times[hour])) : null),
    [heat, selected, hour],
  )
  const recommended = plan?.routes.find((r) => r.recommended)

  return (
    <div className="app">
      <aside className="sidebar">
        <header className="brand">
          <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden>
            <rect width="32" height="32" rx="7" fill="#0f172a" />
            <path d="M6 11h12v9H6zM18 14h4.5l3.5 3.5V20h-8z" fill="#fbbf24" />
            <circle cx="10" cy="21.5" r="2.3" fill="#fff" />
            <circle cx="22" cy="21.5" r="2.3" fill="#fff" />
          </svg>
          <div>
            <h1>Weather-Aware Truck Routing</h1>
            <p>Pick the safest route for this load and departure time.</p>
          </div>
        </header>

        <TripForm onSubmit={onSubmit} loading={loading} />

        {error && <div className="alert error" role="alert">{error}</div>}

        {plan && recommended && (
          <section className="results" aria-live="polite">
            <div className={`recommendation ${plan.recommendation.warning ? 'warn' : ''}`}>
              <div className="rec-title">
                <span className="dot" style={{ background: recommended.color }} />
                Recommended: {recommended.name}
              </div>
              <p>{plan.recommendation.reason}</p>
              {plan.recommendation.warning && <p className="rec-warning">{plan.recommendation.warning}</p>}
              <p className="rec-meta">
                {plan.origin.label} → {plan.destination.label}
                <br />
                Departs {fmtTimeLong(plan.departure)} · {Number(plan.load_lb).toLocaleString()} lb · checkpoints every {plan.interval_mi} mi
              </p>
            </div>
            {plan.warnings.map((w) => (
              <div key={w} className="alert">{w}</div>
            ))}

            <div className="tabs" role="tablist">
              <button role="tab" aria-selected={tab === 'routes'} className={tab === 'routes' ? 'on' : ''} onClick={() => setTab('routes')}>
                Routes ({plan.routes.length})
              </button>
              <button role="tab" aria-selected={tab === 'checkpoints'} className={tab === 'checkpoints' ? 'on' : ''} onClick={() => setTab('checkpoints')}>
                {selected?.name} checkpoints ({selected?.checkpoints.length})
              </button>
            </div>

            {tab === 'routes' ? (
              <div className="route-list">
                {plan.routes.map((r) => (
                  <RouteCard key={r.id} route={r} selected={r.id === selectedId} onSelect={() => setSelectedId(r.id)} />
                ))}
                <details className="method">
                  <summary>How the recommendation works</summary>
                  <ol>
                    <li>Avoid any No Travel miles.</li>
                    <li>Fewest Severe miles, then fewest High miles.</li>
                    <li>Lowest average risk (Low 0 … No Travel 4, weighted by miles).</li>
                    <li>Shortest door-to-door time.</li>
                  </ol>
                  <p>
                    Each stretch between two checkpoints takes the worse of its two checkpoint risks. Weather at a checkpoint is the
                    forecast for the hour the truck gets there.
                  </p>
                </details>
              </div>
            ) : (
              selected && <CheckpointTable route={selected} onFocus={(index) => setFocus({ routeId: selected.id, index, n: Date.now() })} />
            )}
          </section>
        )}

        {!plan && !loading && (
          <section className="empty">
            <h2>How it works</h2>
            <ol>
              <li>Up to 3 truck routes are generated between your origin and destination.</li>
              <li>Each route is checked every 10, 25 or 50 miles, using the forecast for the hour the truck will actually be there.</li>
              <li>Wind, rain and snow are scored with the risk and load rules, and the safest route is recommended.</li>
            </ol>
            <div className="legend-levels">
              {LEVELS.map((l) => (
                <span key={l.name} className="pill" style={{ background: l.color }}>{l.name}</span>
              ))}
            </div>
          </section>
        )}
      </aside>

      <main className="map-wrap">
        <MapView
          plan={plan}
          selectedId={selectedId}
          onSelect={setSelectedId}
          focus={focus}
          heatFrame={showHeat && frames ? frames[hour] : null}
          heatBounds={heat?.bounds}
          truck={truck}
        />
        {loading && (
          <div className="map-loading">
            <span className="spinner dark" aria-hidden /> Finding routes and checking the forecast along each one…
          </div>
        )}
        {plan && (
          <HeatControls
            heat={heat}
            loading={heatLoading}
            error={heatError}
            show={showHeat}
            setShow={setShowHeat}
            variable={variable}
            setVariable={setVariable}
            hour={hour}
            setHour={setHour}
            playing={playing}
            setPlaying={setPlaying}
            truck={truck}
            routeName={selected?.name}
          />
        )}
      </main>
    </div>
  )
}
