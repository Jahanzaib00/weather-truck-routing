import { cellScore, scoreColor } from './risk.js'

const UPSCALE = 4 // bilinear-interpolate scores onto a 4x finer grid before colouring

// Score grid for one hour: Float32Array(nx*ny), NaN where no data.
export function scoreGrid(heat, hour, variable, loadLb) {
  const grid = new Float32Array(heat.nx * heat.ny).fill(NaN)
  heat.cells.forEach((cell, i) => {
    const s = cellScore(variable, heat.wind_mph[i][hour], heat.rain_in[i][hour], heat.snow_in[i][hour], loadLb)
    if (s != null) grid[cell] = s
  })
  return grid
}

// Bilinear sample that ignores missing cells and reports how much data was found
// (used as an alpha factor so the corridor edge fades out instead of cutting off).
function sample(grid, nx, ny, x, y) {
  const x0 = Math.max(0, Math.min(nx - 1, Math.floor(x)))
  const y0 = Math.max(0, Math.min(ny - 1, Math.floor(y)))
  const x1 = Math.min(nx - 1, x0 + 1)
  const y1 = Math.min(ny - 1, y0 + 1)
  const tx = Math.max(0, Math.min(1, x - x0))
  const ty = Math.max(0, Math.min(1, y - y0))
  let sum = 0
  let wsum = 0
  for (const [cx, cy, w] of [
    [x0, y0, (1 - tx) * (1 - ty)],
    [x1, y0, tx * (1 - ty)],
    [x0, y1, (1 - tx) * ty],
    [x1, y1, tx * ty],
  ]) {
    const v = grid[cy * nx + cx]
    if (!Number.isNaN(v) && w > 0) {
      sum += v * w
      wsum += w
    }
  }
  return wsum > 0 ? [sum / wsum, wsum] : [null, 0]
}

// One PNG data URL per hour, drawn once so the slider just swaps images.
export function renderFrames(heat, variable, loadLb, makeCanvas) {
  const { nx, ny } = heat
  const w = nx * UPSCALE
  const h = ny * UPSCALE
  const canvas = makeCanvas(w, h)
  const ctx = canvas.getContext('2d')
  const frames = []
  for (let hour = 0; hour < heat.times.length; hour++) {
    const grid = scoreGrid(heat, hour, variable, loadLb)
    const img = ctx.createImageData(w, h)
    for (let py = 0; py < h; py++) {
      for (let px = 0; px < w; px++) {
        const [score, coverage] = sample(grid, nx, ny, (px + 0.5) / UPSCALE - 0.5, (py + 0.5) / UPSCALE - 0.5)
        const [r, g, b, a] = scoreColor(score)
        const o = (py * w + px) * 4
        img.data[o] = r
        img.data[o + 1] = g
        img.data[o + 2] = b
        img.data[o + 3] = Math.round(a * Math.min(1, coverage * 1.4) * 255)
      }
    }
    ctx.putImageData(img, 0, 0)
    frames.push(canvas.toDataURL('image/png'))
  }
  return frames
}

// Where the truck is at a given time, interpolated between checkpoint ETAs.
export function truckPosition(route, whenMs) {
  const cps = route.checkpoints
  const t = cps.map((c) => Date.parse(c.eta))
  if (whenMs <= t[0]) return { lat: cps[0].lat, lon: cps[0].lon, state: 'not departed' }
  if (whenMs >= t[t.length - 1]) return { lat: cps.at(-1).lat, lon: cps.at(-1).lon, state: 'arrived' }
  const stop = route.stops.find((s) => whenMs >= Date.parse(s.start) && whenMs < Date.parse(s.end))
  if (stop) return { lat: stop.lat, lon: stop.lon, state: stop.kind === 'reset' ? '10-h rest' : '30-min break' }
  let i = 1
  while (t[i] < whenMs) i++
  const f = (whenMs - t[i - 1]) / (t[i] - t[i - 1] || 1)
  return {
    lat: cps[i - 1].lat + (cps[i].lat - cps[i - 1].lat) * f,
    lon: cps[i - 1].lon + (cps[i].lon - cps[i - 1].lon) * f,
    mile: cps[i - 1].mile + (cps[i].mile - cps[i - 1].mile) * f,
    state: 'driving',
  }
}
