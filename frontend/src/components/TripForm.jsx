import { useState } from 'react'
import { nextHourLocal } from '../lib/format.js'
import PlaceInput from './PlaceInput.jsx'

const LOAD_PRESETS = [10000, 25000, 35000, 45000]

export default function TripForm({ onSubmit, loading }) {
  const [origin, setOrigin] = useState({ label: 'Chicago, IL' })
  const [destination, setDestination] = useState({ label: 'Denver, CO' })
  const [departure, setDeparture] = useState(nextHourLocal())
  const [load, setLoad] = useState(35000)
  const [interval, setIntervalMi] = useState(25)
  const [hos, setHos] = useState(true)

  const submit = (e) => {
    e.preventDefault()
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: Number(load),
      interval_mi: interval,
      hos,
    })
  }

  const swap = () => {
    setOrigin(destination)
    setDestination(origin)
  }

  return (
    <form className="trip-form" onSubmit={submit}>
      <div className="places">
        <PlaceInput id="origin" label="Origin" value={origin} onChange={setOrigin} placeholder="City, address or lat,lon" />
        <button type="button" className="swap" onClick={swap} title="Swap origin and destination" aria-label="Swap origin and destination">
          ⇅
        </button>
        <PlaceInput id="destination" label="Destination" value={destination} onChange={setDestination} placeholder="City, address or lat,lon" />
      </div>

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input id="departure" type="datetime-local" value={departure} onChange={(e) => setDeparture(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input id="load" type="number" min="0" max="120000" step="500" value={load} onChange={(e) => setLoad(e.target.value)} required />
        </div>
      </div>
      <div className="presets" aria-label="Load presets">
        {LOAD_PRESETS.map((p) => (
          <button type="button" key={p} className={Number(load) === p ? 'chip on' : 'chip'} onClick={() => setLoad(p)}>
            {(p / 1000).toFixed(0)}k
          </button>
        ))}
      </div>

      <div className="row">
        <div className="field">
          <span className="label">Weather checkpoint every</span>
          <div className="segmented" role="radiogroup" aria-label="Checkpoint interval">
            {[10, 25, 50].map((v) => (
              <button type="button" key={v} role="radio" aria-checked={interval === v} className={interval === v ? 'on' : ''} onClick={() => setIntervalMi(v)}>
                {v} mi
              </button>
            ))}
          </div>
        </div>
      </div>

      <label className="check">
        <input type="checkbox" checked={hos} onChange={(e) => setHos(e.target.checked)} />
        <span>
          Include Hours-of-Service rest
          <small>30-min break after 8 h driving, 10-h reset after 11 h. Shifts ETAs, so the truck meets a different forecast hour.</small>
        </span>
      </label>

      <button className="primary" type="submit" disabled={loading}>
        {loading ? <span className="spinner" aria-hidden /> : null}
        {loading ? 'Planning…' : 'Find safest route'}
      </button>
    </form>
  )
}
