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
