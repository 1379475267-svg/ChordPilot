<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { calculatePlaybackProgress, findActiveChordIndex } from '../utils/timeline.js'

const props = defineProps({
  chords: { type: Array, default: () => [] },
  duration: Number,
  currentTime: { type: Number, default: 0 },
  playing: Boolean
})

const emit = defineEmits(['seek'])
const scrollContainer = ref(null)
const cardElements = ref([])

const activeIndex = computed(() => {
  return findActiveChordIndex(props.chords, props.currentTime, props.duration)
})

const activeChord = computed(() => props.chords[activeIndex.value]?.chord || '—')
const progress = computed(() => {
  return calculatePlaybackProgress(props.currentTime, props.duration)
})

watch(activeIndex, async (index) => {
  if (index < 0) return
  await nextTick()
  const container = scrollContainer.value
  const card = cardElements.value[index]
  if (!container || !card) return
  const target = card.offsetLeft - container.clientWidth / 2 + card.clientWidth / 2
  container.scrollTo({ left: Math.max(0, target), behavior: 'smooth' })
})

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

    <div class="song-progress" aria-hidden="true">
      <i :style="{ width: `${progress}%` }"></i>
    </div>

    <div ref="scrollContainer" class="timeline-scroll">
      <div class="timeline-track">
        <article
          v-for="(item, index) in chords"
          :key="`${item.start}-${item.chord}`"
          :ref="(element) => { if (element) cardElements[index] = element }"
          class="chord-card"
          :class="[confidenceClass(item.confidence), { active: index === activeIndex }]"
          :style="{ '--delay': `${index * 35}ms` }"
          role="button"
          tabindex="0"
          :aria-label="`跳转到 ${formatTime(item.start)}，和弦 ${item.chord}`"
          @click="emit('seek', item.start)"
          @keydown.enter="emit('seek', item.start)"
          @keydown.space.prevent="emit('seek', item.start)"
        >
          <div v-if="index === activeIndex" class="playhead"><i></i></div>
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
  </section>
</template>
