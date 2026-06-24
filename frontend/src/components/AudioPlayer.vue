<script setup>
import { onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  audioUrl: String,
  filename: String,
  duration: Number
})

const emit = defineEmits(['time-update', 'play-state'])
const audioElement = ref(null)

function formatDuration(seconds) {
  const minutes = Math.floor((seconds || 0) / 60)
  const remainder = Math.round((seconds || 0) % 60)
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

function handleTimeUpdate() {
  emit('time-update', audioElement.value?.currentTime || 0)
}

function seekTo(seconds) {
  if (!audioElement.value) return
  audioElement.value.currentTime = Math.max(0, Math.min(seconds, props.duration || seconds))
  emit('time-update', audioElement.value.currentTime)
  audioElement.value.play().catch(() => {})
}

defineExpose({ seekTo })

onBeforeUnmount(() => {
  // Object URL 由父组件统一回收。
})
</script>

<template>
  <section class="player-card glass-card">
    <div class="vinyl-mark"><i class="pi pi-volume-up"></i></div>
    <div class="track-meta">
      <span>正在分析的音频</span>
      <strong>{{ filename }}</strong>
      <small>{{ formatDuration(duration) }}</small>
    </div>
    <audio
      ref="audioElement"
      :src="audioUrl"
      controls
      preload="metadata"
      @timeupdate="handleTimeUpdate"
      @seeked="handleTimeUpdate"
      @play="emit('play-state', true)"
      @pause="emit('play-state', false)"
      @ended="emit('play-state', false)"
    >
      你的浏览器不支持音频播放。
    </audio>
  </section>
</template>
