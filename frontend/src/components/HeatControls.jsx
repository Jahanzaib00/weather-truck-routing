import { useEffect } from 'react'
import { fmtTimeLong } from '../lib/format.js'

const VARIABLES = [
  ['risk', 'Overall risk'],
  ['wind', 'Wind'],
  ['rain', 'Rain'],
  ['snow', 'Snow'],
]

export default function HeatControls({ heat, loading, error, show, setShow, variable, setVariable, hour, setHour, playing, setPlaying, truck, routeName }) {
  useEffect(() => {
    if (!playing || !heat) return
    const id = window.setInterval(() => setHour((h) => (h + 1) % heat.times.length), 450)
    return () => window.clearInterval(id)
  }, [playing, heat, setHour])

  return (
    <div className="heat-controls" aria-label="Weather heatmap controls">
      <div className="hc-top">
        <label className="switch">
          <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} />
          <span>Weather heatmap</span>
        </label>
        <div className="segmented small" role="radiogroup" aria-label="Heatmap variable">
          {VARIABLES.map(([v, label]) => (
            <button key={v} type="button" role="radio" aria-checked={variable === v} className={variable === v ? 'on' : ''} onClick={() => setVariable(v)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {loading && <div className="hc-status"><span className="spinner dark" aria-hidden /> Loading 48-hour forecast along the corridor…</div>}
      {error && <div className="hc-status err">{error}</div>}
      {heat && (
        <>
          <div className="hc-slider">
            <button type="button" className="play" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}>
              {playing ? '❚❚' : '▶'}
            </button>
            <input
              type="range"
              min="0"
              max={heat.times.length - 1}
              value={hour}
              onChange={(e) => {
                setPlaying(false)
                setHour(Number(e.target.value))
              }}
              aria-label="Forecast hour"
            />
            <span className="hc-hour">+{hour}h</span>
          </div>
          <div className="hc-meta">
            <span>{fmtTimeLong(heat.times[hour])}</span>
            {truck && (
              <span className="truck-state">
                {routeName} truck: {truck.state === 'driving' ? `mile ${Math.round(truck.mile)}` : truck.state}
              </span>
            )}
          </div>
          <div className="legend">
            <span>Low</span>
            <div className="ramp" />
            <span>No Travel</span>
          </div>
        </>
      )}
    </div>
  )
}
