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

export const MIN_TIMELINE_ZOOM = 0.45
export const MAX_TIMELINE_ZOOM = 3.2
export const TIMELINE_ZOOM_STEP = 0.25

export function clampTimelineZoom(zoom) {
  return Math.min(MAX_TIMELINE_ZOOM, Math.max(MIN_TIMELINE_ZOOM, Number(zoom) || 1))
}

export function calculateTimelineWidth(duration, viewportWidth = 980, zoom = 1) {
  if (!duration) return viewportWidth
  const pxPerSecond = duration > 240 ? 14 : duration > 120 ? 17 : 21
  return Math.max(viewportWidth, Math.round(duration * pxPerSecond * clampTimelineZoom(zoom)))
}

export function calculateFitZoom(duration, viewportWidth = 980) {
  if (!duration) return 1
  const pxPerSecond = duration > 240 ? 14 : duration > 120 ? 17 : 21
  return clampTimelineZoom(viewportWidth / Math.max(1, duration * pxPerSecond))
}

export function calculateChordWidth(chord, totalWidth, duration) {
  if (!duration) return 150
  const chordDuration = Math.max(0.4, chord.end - chord.start)
  return Math.max(92, Math.round((chordDuration / duration) * totalWidth))
}

export function buildTimelineLayout(chords, duration, viewportWidth = 980, zoom = 1) {
  const baseWidth = calculateTimelineWidth(duration, viewportWidth, zoom)
  if (!chords.length || !duration) {
    return { totalWidth: baseWidth, items: [] }
  }

  let offset = 0
  const items = chords.map((chord) => {
    const width = calculateChordWidth(chord, baseWidth, duration)
    const item = { ...chord, width, offset }
    offset += width
    return item
  })

  return { totalWidth: Math.max(baseWidth, offset), items }
}

export function calculatePlayheadOffset(currentTime, duration, totalWidth) {
  if (!duration || !totalWidth) return 0
  return Math.round((Math.min(duration, Math.max(0, currentTime)) / duration) * totalWidth)
}

export function calculateTimelinePlayheadOffset(items, currentTime, duration, totalWidth) {
  if (!items.length) return calculatePlayheadOffset(currentTime, duration, totalWidth)
  const clampedTime = Math.min(duration, Math.max(0, currentTime))
  const activeIndex = findActiveChordIndex(items, clampedTime, duration)
  const active = items[activeIndex]
  if (!active) return totalWidth

  const chordDuration = Math.max(0.001, active.end - active.start)
  const progress = Math.min(1, Math.max(0, (clampedTime - active.start) / chordDuration))
  return Math.round(active.offset + active.width * progress)
}

export function buildTimelineBars(count = 96) {
  if (count <= 0) return []
  return Array.from({ length: count }, (_, index) => {
    const seed = Math.sin(index * 1.77) + Math.sin(index * 0.37) * 0.65 + Math.cos(index * 0.91) * 0.42
    return Math.round(18 + Math.abs(seed) * 30 + ((index % 7) / 7) * 12)
  })
}

export function buildWaveformBarsFromChannel(channelData, count = 160) {
  if (count <= 0) return []
  if (!channelData?.length) return buildTimelineBars(count)

  const peaks = Array.from({ length: count }, (_, index) => {
    const start = Math.floor((index / count) * channelData.length)
    const end = Math.max(start + 1, Math.floor(((index + 1) / count) * channelData.length))
    let peak = 0
    for (let cursor = start; cursor < end; cursor += 1) {
      peak = Math.max(peak, Math.abs(channelData[cursor] || 0))
    }
    return peak
  })

  const maximum = Math.max(...peaks)
  if (!maximum) return peaks.map(() => 10)

  return peaks.map((peak) => Math.round(10 + (peak / maximum) * 90))
}

export function buildWaveformBarsFromChannels(channels, count = 160, samplesPerBar = 512) {
  if (!channels?.length || !channels[0]?.length) return buildTimelineBars(count)
  if (count <= 0) return []

  const length = channels[0].length
  const peaks = Array.from({ length: count }, (_, index) => {
    const start = Math.floor((index / count) * length)
    const end = Math.max(start + 1, Math.floor(((index + 1) / count) * length))
    const step = Math.max(1, Math.ceil((end - start) / samplesPerBar))
    let peak = 0
    for (const channel of channels) {
      for (let cursor = start; cursor < end; cursor += step) {
        peak = Math.max(peak, Math.abs(channel[cursor] || 0))
      }
    }
    return peak
  })

  const maximum = Math.max(...peaks)
  if (!maximum) return peaks.map(() => 10)
  return peaks.map((peak) => Math.round(10 + (peak / maximum) * 90))
}

export function resampleWaveformBars(bars, count = 160) {
  if (!bars?.length) return buildTimelineBars(count)
  if (count <= 0) return []
  return Array.from({ length: count }, (_, index) => {
    const start = Math.floor((index / count) * bars.length)
    const end = Math.max(start + 1, Math.floor(((index + 1) / count) * bars.length))
    return Math.max(...bars.slice(start, end))
  })
}
