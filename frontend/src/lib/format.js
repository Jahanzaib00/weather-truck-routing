export const fmtMiles = (mi) => `${Math.round(mi).toLocaleString()} mi`

export function fmtDuration(hours) {
  const total = Math.round(hours * 60)
  const h = Math.floor(total / 60)
  const m = total % 60
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}

const dtf = new Intl.DateTimeFormat(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })
const dtfZone = new Intl.DateTimeFormat(undefined, {
  weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
})

export const fmtTime = (iso) => dtf.format(new Date(iso))
export const fmtTimeLong = (iso) => dtfZone.format(new Date(iso))

export const fmtNum = (v, digits = 0, unit = '') => (v == null ? '–' : `${v.toFixed(digits)}${unit}`)

// <input type="datetime-local"> value for "next full hour", in local time.
export function nextHourLocal() {
  const d = new Date(Date.now() + 60 * 60 * 1000)
  d.setMinutes(0, 0, 0)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`
}
