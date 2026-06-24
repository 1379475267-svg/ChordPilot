<script setup>
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton'

const props = defineProps({
  file: File,
  analysisMode: { type: String, default: 'fast' },
  chordRange: { type: String, default: 'basic' },
  loading: Boolean
})

const emit = defineEmits(['update:file', 'update:analysisMode', 'update:chordRange', 'analyze', 'error'])
const fileInput = ref(null)
const dragging = ref(false)

const formattedSize = computed(() => {
  if (!props.file) return ''
  return props.file.size < 1024 * 1024
    ? `${(props.file.size / 1024).toFixed(1)} KB`
    : `${(props.file.size / 1024 / 1024).toFixed(2)} MB`
})

function chooseFile() {
  fileInput.value?.click()
}

function acceptFile(file) {
  if (!file) return
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!['mp3', 'wav'].includes(extension)) {
    emit('error', '请选择 MP3 或 WAV 文件')
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    emit('error', '文件不能超过 50 MB')
    return
  }
  emit('update:file', file)
}

function onFileChange(event) {
  acceptFile(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  dragging.value = false
  acceptFile(event.dataTransfer.files?.[0])
}
</script>

<template>
  <section class="upload-card glass-card">
    <div class="section-heading">
      <div>
        <span class="eyebrow">AUDIO INPUT</span>
        <h2>把歌曲交给 ChordPilot</h2>
        <p>上传一段音频，生成可以继续编辑和练习的和弦草稿。</p>
      </div>
      <span class="step-number">01</span>
    </div>

    <div
      class="drop-zone"
      :class="{ active: dragging, selected: file }"
      @click="chooseFile"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".mp3,.wav,audio/mpeg,audio/wav" hidden @change="onFileChange" />
      <div class="upload-icon"><i :class="file ? 'pi pi-wave-pulse' : 'pi pi-cloud-upload'"></i></div>
      <template v-if="file">
        <strong>{{ file.name }}</strong>
        <span>{{ formattedSize }} · 点击可更换文件</span>
      </template>
      <template v-else>
        <strong>拖入音频，或点击浏览</strong>
        <span>支持 MP3 / WAV，最大 50 MB</span>
      </template>
    </div>

    <div class="settings-grid">
      <fieldset>
        <legend>分析模式</legend>
        <label class="choice-card" :class="{ checked: analysisMode === 'fast' }">
          <RadioButton
            :model-value="analysisMode"
            input-id="mode-fast"
            name="mode"
            value="fast"
            @update:model-value="emit('update:analysisMode', $event)"
          />
          <span><strong>快速模式</strong><small>直接分析，速度更快</small></span>
          <i class="pi pi-bolt"></i>
        </label>
        <label class="choice-card" :class="{ checked: analysisMode === 'clean' }">
          <RadioButton
            :model-value="analysisMode"
            input-id="mode-clean"
            name="mode"
            value="clean"
            @update:model-value="emit('update:analysisMode', $event)"
          />
          <span><strong>干净模式</strong><small>尝试分离人声与鼓点</small></span>
          <i class="pi pi-sparkles"></i>
        </label>
      </fieldset>

      <fieldset>
        <legend>和弦范围</legend>
        <label class="choice-card" :class="{ checked: chordRange === 'basic' }">
          <RadioButton
            :model-value="chordRange"
            input-id="range-basic"
            name="range"
            value="basic"
            @update:model-value="emit('update:chordRange', $event)"
          />
          <span><strong>基础和弦</strong><small>大三和弦与小三和弦</small></span>
          <i class="pi pi-circle"></i>
        </label>
        <label class="choice-card" :class="{ checked: chordRange === 'extended' }">
          <RadioButton
            :model-value="chordRange"
            input-id="range-extended"
            name="range"
            value="extended"
            @update:model-value="emit('update:chordRange', $event)"
          />
          <span><strong>扩展和弦</strong><small>七和弦、挂留与更多色彩</small></span>
          <i class="pi pi-asterisk"></i>
        </label>
      </fieldset>
    </div>

    <Button
      class="analyze-button"
      label="开始分析"
      icon="pi pi-play"
      :loading="loading"
      :disabled="!file || loading"
      @click="emit('analyze')"
    />
  </section>
</template>
