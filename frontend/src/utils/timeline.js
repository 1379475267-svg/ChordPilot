export function findActiveChordIndex(chords, currentTime, duration = 0) {
  if (!chords.length) return -1
  const index = chords.findIndex(
    (item) => currentTime >= item.start && currentTime < item.end
  )
  if (index >= 0) return index
  return currentTime >= duration ? chords.length - 1 : 0
}

export function calculatePlaybackProgress(currentTime, duration) {
  if (!duration) return 0
  return Math.min(100, Math.max(0, (currentTime / duration) * 100))
}

export function calculateTimelineWidth(duration, viewportWidth = 980) {
  if (!duration) return viewportWidth
  const pxPerSecond = duration > 240 ? 14 : duration > 120 ? 17 : 21
  return Math.max(viewportWidth, Math.round(duration * pxPerSecond))
}

export function calculateChordWidth(chord, totalWidth, duration) {
  if (!duration) return 150
  const chordDuration = Math.max(0.4, chord.end - chord.start)
  return Math.max(92, Math.round((chordDuration / duration) * totalWidth))
}

export function calculatePlayheadOffset(currentTime, duration, totalWidth) {
  if (!duration || !totalWidth) return 0
  return Math.round((Math.min(duration, Math.max(0, currentTime)) / duration) * totalWidth)
}

export function buildTimelineBars(count = 96) {
  return Array.from({ length: count }, (_, index) => {
    const seed = Math.sin(index * 1.77) + Math.sin(index * 0.37) * 0.65 + Math.cos(index * 0.91) * 0.42
    return Math.round(18 + Math.abs(seed) * 30 + ((index % 7) / 7) * 12)
  })
}
