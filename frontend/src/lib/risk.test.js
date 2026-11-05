import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cellScore, scoreColor, windScore } from './risk.js'
import { truckPosition } from './heatFrames.js'

test('wind score matches level thresholds', () => {
  assert.equal(windScore(25, 0), 1)
  assert.equal(windScore(35, 0), 2)
  assert.equal(windScore(55, 0), 4)
  assert.equal(windScore(10, 0), 0)
})

test('load rules raise wind score like the backend', () => {
  assert.equal(windScore(46, 30001), 4)
  assert.equal(windScore(40, 40001), 3)
  assert.ok(windScore(40, 40000) < 3)
})

test('overall score is the worst variable', () => {
  assert.equal(cellScore('risk', 10, 0.5, 0, 0), 3)
  assert.equal(cellScore('snow', 60, 0, 0, 0), 0)
  assert.equal(cellScore('risk', null, null, null, 0), null)
})

test('calm weather is transparent', () => {
  assert.equal(scoreColor(0)[3], 0)
  assert.ok(scoreColor(4)[3] > 0.5)
})

test('truck position interpolates between checkpoints and respects rest stops', () => {
  const route = {
    checkpoints: [
      { lat: 0, lon: 0, mile: 0, eta: '2026-01-01T00:00:00Z' },
      { lat: 0, lon: 10, mile: 100, eta: '2026-01-01T10:00:00Z' },
    ],
    stops: [{ kind: 'break', lat: 0, lon: 8, start: '2026-01-01T08:00:00Z', end: '2026-01-01T08:30:00Z' }],
  }
  const mid = truckPosition(route, Date.parse('2026-01-01T05:00:00Z'))
  assert.equal(mid.state, 'driving')
  assert.equal(mid.lon, 5)
  assert.equal(truckPosition(route, Date.parse('2026-01-01T08:10:00Z')).state, '30-min break')
  assert.equal(truckPosition(route, Date.parse('2026-01-02T00:00:00Z')).state, 'arrived')
})
