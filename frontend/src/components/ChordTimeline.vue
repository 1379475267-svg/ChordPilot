<script setup>
import { computed, nextTick, onBeforeUnmount, onBeforeUpdate, ref, watch } from 'vue'
import {
  buildTimelineBars,
  calculateChordWidth,
  calculatePlaybackProgress,
  calculatePlayheadOffset,
  calculateTimelineWidth,
  findActiveChordIndex
} from '../utils/timeline.js'

const props = defineProps({
  chords: { type: Array, default: () => [] },
  duration: Number,
  currentTime: { type: Number, default: 0 },
  playing: Boolean
})

const emit = defineEmits(['seek'])
const scrollContainer = ref(null)
const timelineCanvas = ref(null)
const cardElements = ref([])
const waveformBars = buildTimelineBars(118)
let scrollFrame = null

const activeIndex = computed(() => {
  return findActiveChordIndex(props.chords, props.currentTime, props.duration)
})

const activeChord = computed(() => props.chords[activeIndex.value]?.chord || '—')
const totalWidth = computed(() => calculateTimelineWidth(props.duration))
const progress = computed(() => {
  return calculatePlaybackProgress(props.currentTime, props.duration)
})
const playheadOffset = computed(() => {
  return calculatePlayheadOffset(props.currentTime, props.duration, totalWidth.value)
})
const activeItem = computed(() => props.chords[activeIndex.value])
const activeRange = computed(() => {
  if (!activeItem.value) return '—'
  return `${formatTime(activeItem.value.start)} — ${formatTime(activeItem.value.end)}`
})
const timelineItems = computed(() => {
  return props.chords.map((item) => ({
    ...item,
    width: calculateChordWidth(item, totalWidth.value, props.duration)
  }))
})

onBeforeUpdate(() => {
  cardElements.value = []
})

onBeforeUnmount(() => {
  if (scrollFrame) window.cancelAnimationFrame(scrollFrame)
})

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
    if (!props.playing) return
    if (scrollFrame) return
    scrollFrame = window.requestAnimationFrame(() => {
      scrollFrame = null
      centerPlayhead()
    })
  }
)

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
        <div class="waveform-strip" aria-hidden="true">
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
            v-for="tick in 7"
            :key="tick"
            :style="{ left: `${((tick - 1) / 6) * 100}%` }"
          >
            {{ formatTime(((tick - 1) / 6) * duration) }}
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
