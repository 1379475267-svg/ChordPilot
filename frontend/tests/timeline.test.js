import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildTimelineBars,
  buildWaveformBarsFromChannel,
  calculateChordWidth,
  calculateFitZoom,
  calculatePlaybackProgress,
  calculatePlayheadOffset,
  calculateTimelineWidth,
  clampTimelineZoom,
  MAX_TIMELINE_ZOOM,
  MIN_TIMELINE_ZOOM,
  findActiveChordIndex
} from '../src/utils/timeline.js'

const chords = [
  { start: 0, end: 2, chord: 'C' },
  { start: 2, end: 4, chord: 'G' },
  { start: 4, end: 6, chord: 'Am' }
]

test('finds the chord containing the playback time', () => {
  assert.equal(findActiveChordIndex(chords, 0, 6), 0)
  assert.equal(findActiveChordIndex(chords, 2.1, 6), 1)
  assert.equal(findActiveChordIndex(chords, 5.8, 6), 2)
})

test('keeps the final chord active when playback ends', () => {
  assert.equal(findActiveChordIndex(chords, 6, 6), 2)
})

test('clamps playback progress to zero and one hundred percent', () => {
  assert.equal(calculatePlaybackProgress(-1, 6), 0)
  assert.equal(calculatePlaybackProgress(3, 6), 50)
  assert.equal(calculatePlaybackProgress(8, 6), 100)
})

test('sizes timeline elements from real playback duration', () => {
  const width = calculateTimelineWidth(180, 980)
  assert.ok(width >= 980)
  assert.equal(calculatePlayheadOffset(90, 180, width), Math.round(width / 2))
  assert.ok(calculateChordWidth({ start: 0, end: 8 }, width, 180) > calculateChordWidth({ start: 0, end: 2 }, width, 180))
})

test('builds deterministic decorative waveform bars', () => {
  const bars = buildTimelineBars(8)
  assert.equal(bars.length, 8)
  assert.deepEqual(bars, buildTimelineBars(8))
  assert.ok(bars.every((height) => height >= 18))
})

test('clamps timeline zoom and fits songs into the viewport', () => {
  assert.equal(clampTimelineZoom(0.1), MIN_TIMELINE_ZOOM)
  assert.equal(clampTimelineZoom(9), MAX_TIMELINE_ZOOM)
  assert.ok(calculateTimelineWidth(180, 980, 2) > calculateTimelineWidth(180, 980, 1))
  assert.ok(calculateFitZoom(600, 980) >= MIN_TIMELINE_ZOOM)
})

test('builds waveform bars from real channel samples', () => {
  const samples = Float32Array.from([0, 0.25, -0.5, 1, -1, 0.2, 0.1, 0])
  const bars = buildWaveformBarsFromChannel(samples, 4)
  assert.equal(bars.length, 4)
  assert.ok(Math.max(...bars) <= 100)
  assert.ok(Math.min(...bars) >= 10)
  assert.ok(bars[1] > bars[0])
})
