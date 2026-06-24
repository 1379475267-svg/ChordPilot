<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import {
  PhHeadphones,
  PhMagicWand,
  PhMusicNotes,
  PhPianoKeys,
  PhSparkle,
  PhVinylRecord,
  PhWaveform
} from '@phosphor-icons/vue'

import AudioPlayer from './components/AudioPlayer.vue'
import AudioUploader from './components/AudioUploader.vue'
import ChordTable from './components/ChordTable.vue'
import ChordTimeline from './components/ChordTimeline.vue'
import ExportPanel from './components/ExportPanel.vue'

const toast = useToast()
const selectedFile = ref(null)
const analysisMode = ref('fast')
const chordRange = ref('basic')
const loading = ref(false)
const result = ref(null)
const audioUrl = ref('')
const audioPlayer = ref(null)
const currentTime = ref(0)
const isPlaying = ref(false)
const backendStatus = ref('checking')
let healthTimer = null

const hasResult = computed(() => Boolean(result.value?.chords?.length))
const backendStatusText = computed(() => {
  if (backendStatus.value === 'online') return '分析服务已连接'
  if (backendStatus.value === 'offline') return '分析服务未启动'
  return '正在连接分析服务'
})

async function checkBackend() {
  backendStatus.value = 'checking'
  try {
    const response = await fetch('/api/health', { cache: 'no-store' })
    backendStatus.value = response.ok ? 'online' : 'offline'
  } catch {
    backendStatus.value = 'offline'
  }
  return backendStatus.value === 'online'
}

function showError(message) {
  toast.add({ severity: 'error', summary: '暂时无法分析', detail: message, life: 4500 })
}

async function analyze() {
  if (!selectedFile.value) return

  if (!(await checkBackend())) {
    showError('后端分析服务没有启动。请运行项目根目录的 start.ps1，然后重新分析。')
    return
  }

  loading.value = true
  result.value = null

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('analysis_mode', analysisMode.value)
  formData.append('chord_range', chordRange.value)

  try {
    const response = await fetch('/api/analyze', { method: 'POST', body: formData })
    const contentType = response.headers.get('content-type') || ''
    const payload = contentType.includes('application/json')
      ? await response.json()
      : { detail: await response.text() }
    if (!response.ok) throw new Error(payload.detail || '服务器返回了未知错误')

    if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = URL.createObjectURL(selectedFile.value)
    currentTime.value = 0
    isPlaying.value = false
    result.value = payload
    toast.add({
      severity: payload.warning ? 'warn' : 'success',
      summary: payload.warning ? '分析完成，已使用回退方案' : '和弦草稿已生成',
      detail: payload.warning || `识别出 ${payload.chords.length} 个和弦片段`,
      life: 4500
    })
  } catch (error) {
    showError(error.message || '请确认后端服务已启动')
  } finally {
    loading.value = false
  }
}

async function copyProgression() {
  const text = result.value.chords.map((item) => item.chord).join(' | ')
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: '已复制', detail: text, life: 3000 })
  } catch {
    showError('浏览器未允许访问剪贴板')
  }
}

function clearAll() {
  selectedFile.value = null
  result.value = null
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  audioUrl.value = ''
  currentTime.value = 0
  isPlaying.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onBeforeUnmount(() => {
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  if (healthTimer) window.clearInterval(healthTimer)
})

onMounted(() => {
  checkBackend()
  healthTimer = window.setInterval(checkBackend, 10000)
})
</script>

<template>
  <div class="app-shell">
    <Toast />
    <div class="ambient ambient-one"></div>
    <div class="ambient ambient-two"></div>

    <header class="site-header">
      <a class="brand" href="#" aria-label="ChordPilot 首页">
        <span class="brand-icon"><PhWaveform :size="24" weight="bold" /></span>
        <span><strong>ChordPilot</strong><small>智能扒和弦助手</small></span>
      </a>
      <div class="header-status">
        <div class="service-pill" :class="backendStatus">
          <i class="pi pi-circle-fill"></i>
          {{ backendStatusText }}
        </div>
        <div class="version-pill"><i class="pi pi-sparkles"></i> v0.1 · Local AI</div>
      </div>
    </header>

    <main>
      <section class="hero">
        <div class="hero-copy">
          <span class="hero-kicker"><PhSparkle :size="16" weight="fill" /> 把声音变成可以练习的和弦</span>
          <h1>
            <span>听见旋律，</span>
            <em>看见和弦。</em>
          </h1>
          <p>上传歌曲，ChordPilot 会分析和声结构，生成直观的和弦时间轴。它不替你演奏，但能让第一遍扒谱轻松很多。</p>
          <div class="hero-stats">
            <span><PhPianoKeys :size="20" /><strong>12</strong><small>全部根音</small></span>
            <span><PhMagicWand :size="20" /><strong>15</strong><small>和弦类型</small></span>
            <span><PhHeadphones :size="20" /><strong>Local</strong><small>隐私优先</small></span>
          </div>
        </div>
        <div class="hero-visual" aria-hidden="true">
          <div class="studio-poster">
            <div class="poster-grain"></div>
            <div class="poster-topline">
              <span>HARMONIC<br />STUDIO</span>
              <PhMusicNotes :size="34" weight="duotone" />
            </div>
            <div class="record-wrap">
              <div class="record">
                <PhVinylRecord :size="170" weight="duotone" />
                <div class="record-label">CP</div>
              </div>
              <div class="tone-arm"></div>
            </div>
            <div class="poster-wave">
              <i v-for="index in 28" :key="index" :style="{ '--i': index }"></i>
            </div>
            <div class="poster-caption">
              <strong>LISTEN · ANALYZE · PLAY</strong>
              <span>CHORD PILOT / 01</span>
            </div>
          </div>
          <div class="floating-chord chord-c">C</div>
          <div class="floating-chord chord-g">G</div>
          <div class="floating-chord chord-am">Am</div>
          <div class="floating-chord chord-f">F</div>
        </div>
      </section>

      <AudioUploader
        v-if="!hasResult"
        v-model:file="selectedFile"
        v-model:analysis-mode="analysisMode"
        v-model:chord-range="chordRange"
        :loading="loading"
        @analyze="analyze"
        @error="showError"
      />

      <section v-if="loading" class="loading-overlay" aria-live="polite">
        <ProgressSpinner stroke-width="3" />
        <strong>正在聆听和声结构…</strong>
        <span>提取色度特征并匹配和弦模板</span>
      </section>

      <div v-if="hasResult" class="results">
        <AudioPlayer
          ref="audioPlayer"
          :audio-url="audioUrl"
          :filename="result.filename"
          :duration="result.duration"
          @time-update="currentTime = $event"
          @play-state="isPlaying = $event"
        />
        <ChordTimeline
          :chords="result.chords"
          :duration="result.duration"
          :current-time="currentTime"
          :playing="isPlaying"
          @seek="audioPlayer?.seekTo($event)"
        />
        <div class="results-grid">
          <ChordTable :chords="result.chords" />
          <aside class="insight-card glass-card">
            <span class="eyebrow">SESSION NOTE</span>
            <h3>这是一份聪明的草稿，<br />不是最后的乐谱。</h3>
            <p>复杂编曲、转位和弦与强烈鼓点都可能影响识别。建议边听边核对，把它当作扒谱的起点。</p>
            <div class="mode-summary">
              <span><i class="pi pi-bolt"></i> {{ result.analysis_mode === 'clean' ? '干净模式' : '快速模式' }}</span>
              <span><i class="pi pi-sliders-h"></i> {{ result.chord_range === 'extended' ? '扩展和弦' : '基础和弦' }}</span>
            </div>
          </aside>
        </div>
        <ExportPanel :chords="result.chords" :result="result" @copy="copyProgression" @clear="clearAll" />
      </div>
    </main>

    <footer>
      <span>ChordPilot <b>v0.1</b></span>
      <p>为练习、学习与音乐转写提供一个更好的开始。</p>
      <span>Made for musicians <i class="pi pi-heart-fill"></i></span>
    </footer>
  </div>
</template>
