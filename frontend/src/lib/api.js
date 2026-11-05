async function request(url, options) {
  let res
  try {
    res = await fetch(url, options)
  } catch {
    throw new Error('Cannot reach the server. Check your connection and try again.')
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.error || `Request failed (HTTP ${res.status}).`)
  return body
}

export const planTrip = (payload) =>
  request('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const fetchHeatmap = (planId) => request(`/api/plan/${planId}/heatmap`)

export const searchPlaces = (q, signal) =>
  request(`/api/geocode?q=${encodeURIComponent(q)}`, { signal }).then((b) => b.results)
