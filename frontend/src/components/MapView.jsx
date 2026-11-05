import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { CircleMarker, ImageOverlay, MapContainer, Marker, Pane, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import { levelInfo } from '../lib/risk.js'
import { fmtDuration, fmtMiles, fmtNum, fmtTimeLong } from '../lib/format.js'

const US_CENTER = [39.5, -97]

function FitToPlan({ plan }) {
  const map = useMap()
  useEffect(() => {
    if (!plan) return
    const pts = plan.routes.flatMap((r) => r.geometry)
    if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [40, 40] })
  }, [plan, map])
  return null
}

function FocusCheckpoint({ focus, markers }) {
  const map = useMap()
  useEffect(() => {
    if (!focus) return
    const m = markers.current[`${focus.routeId}-${focus.index}`]
    if (!m) return
    map.flyTo(m.getLatLng(), Math.max(map.getZoom(), 8), { duration: 0.6 })
    setTimeout(() => m.openPopup(), 650)
  }, [focus, map, markers])
  return null
}

const badgeIcon = (route) =>
  L.divIcon({
    className: 'route-badge-icon',
    html: `<div class="route-badge" style="--c:${route.color}">${route.recommended ? '★ ' : ''}${route.id} · ${fmtMiles(route.distance_mi)} · ${fmtDuration(route.total_hours)}<br><small>Severe ${Math.round(route.miles_by_level[3])} mi · High ${Math.round(route.miles_by_level[2])} mi${route.miles_by_level[4] ? ` · No Travel ${Math.round(route.miles_by_level[4])} mi` : ''}</small></div>`,
    iconSize: null,
  })

const endIcon = (label, cls) => L.divIcon({ className: '', html: `<div class="end-pin ${cls}">${label}</div>`, iconSize: [26, 26], iconAnchor: [13, 13] })
const stopIcon = (kind) =>
  L.divIcon({ className: '', html: `<div class="stop-pin">${kind === 'reset' ? '10h' : '30m'}</div>`, iconSize: [30, 18], iconAnchor: [15, 9] })
const truckIcon = L.divIcon({
  className: '',
  html: `<div class="truck-pin"><svg viewBox="0 0 24 24" width="18" height="18"><path fill="#fbbf24" d="M2 7h11v8H2zM13 10h4l3 3v2h-7z"/><circle cx="6" cy="16.5" r="1.8" fill="#fff"/><circle cx="16.5" cy="16.5" r="1.8" fill="#fff"/></svg></div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
})

function CheckpointPopup({ route, cp }) {
  const lv = levelInfo(cp.level)
  return (
    <div className="cp-popup">
      <div className="cp-popup-head">
        <b>{route.name}</b> · mile {Math.round(cp.mile)}
      </div>
      <div>ETA {fmtTimeLong(cp.eta)}</div>
      <div className="pill" style={{ background: lv.color }}>{lv.name}</div>
      <table>
        <tbody>
          <tr><td>Wind</td><td>{fmtNum(cp.wind_mph, 0, ' mph')} (gust {fmtNum(cp.gust_mph, 0)})</td></tr>
          <tr><td>Rain</td><td>{fmtNum(cp.rain_in, 2, ' in/h')}</td></tr>
          <tr><td>Snow</td><td>{fmtNum(cp.snow_in, 2, ' in/h')}</td></tr>
        </tbody>
      </table>
      {cp.reasons.length > 0 && <div className="reasons">{cp.reasons.join(' · ')}</div>}
    </div>
  )
}

export default function MapView({ plan, selectedId, onSelect, focus, heatFrame, heatBounds, truck }) {
  const markers = useRef({})
  const ordered = useMemo(() => {
    if (!plan) return []
    // Draw the selected route last so it sits on top.
    return [...plan.routes].sort((a, b) => (a.id === selectedId) - (b.id === selectedId))
  }, [plan, selectedId])

  return (
    <MapContainer center={US_CENTER} zoom={4} preferCanvas className="map" zoomControl>
      <TileLayer
        attribution='Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        maxZoom={16}
      />
      <Pane name="labels" style={{ zIndex: 330, pointerEvents: 'none' }}>
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
        />
      </Pane>
      <Pane name="heat" style={{ zIndex: 350 }}>
        {heatFrame && heatBounds && <ImageOverlay url={heatFrame} bounds={heatBounds} opacity={1} className="heat-image" />}
      </Pane>
      <FitToPlan plan={plan} />
      <FocusCheckpoint focus={focus} markers={markers} />

      {ordered.map((route) => {
        const selected = route.id === selectedId
        return (
          <Pane key={route.id} name={`route-${route.id}`} style={{ zIndex: selected ? 460 : 420 }}>
            {selected ? (
              <>
                <Polyline positions={route.geometry} pathOptions={{ color: '#0f172a', weight: 10, opacity: 0.85 }} />
                {route.risk_segments.map((seg, i) => (
                  <Polyline key={i} positions={seg.coords} pathOptions={{ color: levelInfo(seg.level).color, weight: 6, opacity: 1 }} />
                ))}
              </>
            ) : (
              <Polyline
                positions={route.geometry}
                pathOptions={{ color: route.color, weight: 5, opacity: 0.55 }}
                eventHandlers={{ click: () => onSelect(route.id) }}
              />
            )}
            {route.checkpoints.map((cp, i) => (
              <CircleMarker
                key={i}
                center={[cp.lat, cp.lon]}
                radius={selected ? 6 : 3.5}
                ref={(m) => {
                  if (m) markers.current[`${route.id}-${i}`] = m
                }}
                pathOptions={{
                  color: selected ? '#fff' : levelInfo(cp.level).color,
                  weight: selected ? 2 : 1,
                  fillColor: levelInfo(cp.level).color,
                  fillOpacity: selected ? 1 : 0.6,
                }}
                eventHandlers={{ click: () => onSelect(route.id) }}
              >
                <Popup>
                  <CheckpointPopup route={route} cp={cp} />
                </Popup>
              </CircleMarker>
            ))}
            {selected &&
              route.stops.map((s, i) => (
                <Marker key={`s${i}`} position={[s.lat, s.lon]} icon={stopIcon(s.kind)}>
                  <Popup>
                    <b>{s.kind === 'reset' ? '10-hour rest (HOS)' : '30-minute break (HOS)'}</b>
                    <br />
                    Mile {Math.round(s.mile)} · {fmtTimeLong(s.start)} → {fmtTimeLong(s.end)}
                  </Popup>
                </Marker>
              ))}
            <Marker
              position={route.geometry[Math.floor(route.geometry.length * (0.35 + 0.15 * 'ABC'.indexOf(route.id)))]}
              icon={badgeIcon(route)}
              eventHandlers={{ click: () => onSelect(route.id) }}
              zIndexOffset={selected ? 1000 : 0}
            />
          </Pane>
        )
      })}

      {plan && (
        <>
          <Marker position={[plan.origin.lat, plan.origin.lon]} icon={endIcon('A', 'start')}>
            <Popup>Origin: {plan.origin.label}</Popup>
          </Marker>
          <Marker position={[plan.destination.lat, plan.destination.lon]} icon={endIcon('B', 'end')}>
            <Popup>Destination: {plan.destination.label}</Popup>
          </Marker>
        </>
      )}
      {truck && <Marker position={[truck.lat, truck.lon]} icon={truckIcon} zIndexOffset={2000} interactive={false} />}
    </MapContainer>
  )
}
