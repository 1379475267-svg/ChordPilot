<script setup>
import { computed, nextTick, onBeforeUnmount, onBeforeUpdate, ref, watch } from 'vue'
import {
  buildTimelineLayout,
  buildWaveformBarsFromChannels,
  buildTimelineBars,
  calculateFitZoom,
  calculatePlaybackProgress,
  calculateTimelinePlayheadOffset,
  clampTimelineZoom,
  findActiveChordIndex,
  resampleWaveformBars
} from '../utils/timeline.js'

const props = defineProps({
  chords: { type: Array, default: () => [] },
  duration: Number,
  currentTime: { type: Number, default: 0 },
  audioFile: File,
  playing: Boolean
})

const emit = defineEmits(['seek'])
const scrollContainer = ref(null)
const timelineCanvas = ref(null)
const cardElements = ref([])
const zoomLevel = ref(1)
const followPlayback = ref(true)
const decodedWaveform = ref(null)
const waveformStatus = ref('fallback')
let scrollFrame = null
let waveformRequestId = 0
const MAX_WAVEFORM_DECODE_BYTES = 20 * 1024 * 1024
const WAVEFORM_SOURCE_BARS = 420

const activeIndex = computed(() => {
  return findActiveChordIndex(props.chords, props.currentTime, props.duration)
})

const activeChord = computed(() => props.chords[activeIndex.value]?.chord || '—')
const zoomPercent = computed(() => Math.round(zoomLevel.value * 100))
const timelineLayout = computed(() => buildTimelineLayout(props.chords, props.duration, 980, zoomLevel.value))
const totalWidth = computed(() => timelineLayout.value.totalWidth)
const waveformBarCount = computed(() => Math.max(96, Math.min(420, Math.round(totalWidth.value / 12))))
const waveformBars = computed(() => {
  if (decodedWaveform.value) {
    return resampleWaveformBars(decodedWaveform.value, waveformBarCount.value)
  }
  return buildTimelineBars(waveformBarCount.value)
})
const waveformLabel = computed(() => {
  if (waveformStatus.value === 'loading') return '解析波形中'
  if (waveformStatus.value === 'ready') return '真实波形'
  return '波形草图'
})
const progress = computed(() => {
  return calculatePlaybackProgress(props.currentTime, props.duration)
})
const playheadOffset = computed(() => {
  return calculateTimelinePlayheadOffset(
    timelineLayout.value.items,
    props.currentTime,
    props.duration,
    totalWidth.value
  )
})
const activeItem = computed(() => props.chords[activeIndex.value])
const activeRange = computed(() => {
  if (!activeItem.value) return '—'
  return `${formatTime(activeItem.value.start)} — ${formatTime(activeItem.value.end)}`
})
const timelineItems = computed(() => timelineLayout.value.items)
const timeTicks = computed(() => {
  return Array.from({ length: 7 }, (_, index) => {
    const time = (index / 6) * props.duration
    return {
      time,
      offset: calculateTimelinePlayheadOffset(
        timelineLayout.value.items,
        time,
        props.duration,
        totalWidth.value
      )
    }
  })
})

onBeforeUpdate(() => {
  cardElements.value = []
})

onBeforeUnmount(() => {
  if (scrollFrame) window.cancelAnimationFrame(scrollFrame)
})

watch(
  () => props.audioFile,
  (file) => {
    decodeWaveform(file)
  },
  { immediate: true }
)

watch(
  () => [activeIndex.value, props.playing],
  async ([index]) => {
    if (index < 0) return
    await nextTick()
    if (!props.playing) centerActiveCard(index)
  }
)

watch(
  () => props.currentTime,
  () => {
    if (!props.playing || !followPlayback.value) return
    if (scrollFrame) return
    scrollFrame = window.requestAnimationFrame(() => {
      scrollFrame = null
      centerPlayhead()
    })
  }
)

async function decodeWaveform(file) {
  const requestId = ++waveformRequestId
  decodedWaveform.value = null
  if (!file) {
    waveformStatus.value = 'fallback'
    return
  }

  if (file.size > MAX_WAVEFORM_DECODE_BYTES) {
    waveformStatus.value = 'fallback'
    return
  }

  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) {
    waveformStatus.value = 'fallback'
    return
  }

  waveformStatus.value = 'loading'
  let context = null
  try {
    const arrayBuffer = await file.arrayBuffer()
    context = new AudioContextClass()
    const audioBuffer = await context.decodeAudioData(arrayBuffer)
    if (requestId !== waveformRequestId) return
    const channels = Array.from(
      { length: audioBuffer.numberOfChannels },
      (_, index) => audioBuffer.getChannelData(index)
    )
    decodedWaveform.value = buildWaveformBarsFromChannels(channels, WAVEFORM_SOURCE_BARS)
    waveformStatus.value = 'ready'
  } catch {
    if (requestId === waveformRequestId) waveformStatus.value = 'fallback'
  } finally {
    if (context?.close) context.close()
  }
}

function centerActiveCard(index) {
  const container = scrollContainer.value
  const card = cardElements.value[index]
  if (!container || !card) return
  const target = card.offsetLeft - container.clientWidth / 2 + card.clientWidth / 2
  container.scrollTo({ left: Math.max(0, target), behavior: 'smooth' })
}

function centerPlayhead() {
  const container = scrollContainer.value
  const canvas = timelineCanvas.value
  if (!container || !canvas) return
  const maximum = Math.max(0, canvas.scrollWidth - container.clientWidth)
  const target = Math.min(maximum, Math.max(0, playheadOffset.value - container.clientWidth * 0.42))
  container.scrollTo({ left: target, behavior: 'smooth' })
}

async function seekTo(item, index) {
  emit('seek', item.start)
  await nextTick()
  centerActiveCard(index)
}

async function setZoom(nextZoom) {
  zoomLevel.value = clampTimelineZoom(nextZoom)
  await nextTick()
  if (followPlayback.value) centerPlayhead()
}

function zoomOut() {
  setZoom(zoomLevel.value - 0.25)
}

function zoomIn() {
  setZoom(zoomLevel.value + 0.25)
}

function fitTimeline() {
  const viewportWidth = scrollContainer.value?.clientWidth || 980
  setZoom(calculateFitZoom(props.duration, viewportWidth))
}

function toggleFollowPlayback() {
  followPlayback.value = !followPlayback.value
  if (followPlayback.value) centerPlayhead()
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60)
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

function confidenceClass(confidence) {
  if (confidence >= 0.75) return 'high'
  if (confidence >= 0.55) return 'medium'
  return 'low'
}
</script>

<template>
  <section class="timeline-section glass-card">
    <div class="section-heading compact">
      <div>
        <span class="eyebrow">CHORD MAP</span>
        <h2>和弦时间轴</h2>
      </div>
      <div class="timeline-live">
        <span class="now-playing" :class="{ playing }">
          <i></i>
          {{ activeChord }}
        </span>
        <span class="duration-label">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
      </div>
    </div>

    <div class="timeline-tools" aria-label="时间轴缩放控制">
      <button type="button" @click="zoomOut">缩小</button>
      <span>{{ zoomPercent }}%</span>
      <button type="button" @click="zoomIn">放大</button>
      <button type="button" @click="fitTimeline">适应全曲</button>
      <button
        type="button"
        :class="{ active: followPlayback }"
        :aria-pressed="followPlayback"
        @click="toggleFollowPlayback"
      >
        跟随播放
      </button>
    </div>

    <div class="timeline-console">
      <div class="console-readout">
        <span>NOW</span>
        <strong>{{ activeChord }}</strong>
        <small>{{ activeRange }}</small>
      </div>
      <div class="song-progress" aria-hidden="true">
        <i :style="{ width: `${progress}%` }"></i>
      </div>
      <div class="console-readout right">
        <span>POSITION</span>
        <strong>{{ Math.round(progress) }}%</strong>
        <small>{{ playing ? '正在播放' : '等待播放' }}</small>
      </div>
    </div>

    <div ref="scrollContainer" class="timeline-scroll">
      <div
        ref="timelineCanvas"
        class="timeline-canvas"
        :style="{ width: `${totalWidth}px`, '--playhead-x': `${playheadOffset}px`, '--progress': `${progress}%` }"
      >
        <div
          class="waveform-strip"
          :class="waveformStatus"
          :style="{ '--waveform-bars': waveformBars.length }"
          aria-hidden="true"
        >
          <span class="waveform-caption">{{ waveformLabel }}</span>
          <i
            v-for="(height, index) in waveformBars"
            :key="index"
            :style="{ height: `${height}%` }"
          ></i>
        </div>
        <div class="global-playhead" :class="{ playing }" aria-hidden="true">
          <span></span>
        </div>
        <div class="time-ruler" aria-hidden="true">
          <span
            v-for="tick in timeTicks"
            :key="tick.time"
            :style="{ left: `${tick.offset}px` }"
          >
            {{ formatTime(tick.time) }}
          </span>
        </div>
        <div class="timeline-track">
        <article
          v-for="(item, index) in timelineItems"
          :key="`${item.start}-${item.chord}`"
          :ref="(element) => { if (element) cardElements[index] = element }"
          class="chord-card"
          :class="[confidenceClass(item.confidence), { active: index === activeIndex }]"
          :style="{ '--delay': `${index * 18}ms`, width: `${item.width}px` }"
          role="button"
          tabindex="0"
          :aria-label="`跳转到 ${formatTime(item.start)}，和弦 ${item.chord}`"
          @click="seekTo(item, index)"
          @keydown.enter="seekTo(item, index)"
          @keydown.space.prevent="seekTo(item, index)"
        >
          <div class="chord-index">{{ String(index + 1).padStart(2, '0') }}</div>
          <strong>{{ item.chord }}</strong>
          <span>{{ formatTime(item.start) }} — {{ formatTime(item.end) }}</span>
          <div class="confidence-bar">
            <i :style="{ width: `${item.confidence * 100}%` }"></i>
          </div>
          <small>{{ Math.round(item.confidence * 100) }}% 置信度</small>
        </article>
        </div>
      </div>
    </div>
  </section>
</template>
