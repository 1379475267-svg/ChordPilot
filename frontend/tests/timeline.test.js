import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildTimelineBars,
  calculateChordWidth,
  calculatePlaybackProgress,
  calculatePlayheadOffset,
  calculateTimelineWidth,
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
