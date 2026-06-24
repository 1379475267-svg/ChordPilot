<script setup>
import Button from 'primevue/button'

const props = defineProps({
  chords: { type: Array, default: () => [] },
  result: Object
})

const emit = defineEmits(['copy', 'clear'])

function download(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function exportTxt() {
  const progression = props.chords.map((item) => item.chord).join(' | ')
  const details = props.chords
    .map((item) => `${item.start.toFixed(2)}s - ${item.end.toFixed(2)}s\t${item.chord}\t${Math.round(item.confidence * 100)}%`)
    .join('\n')
  download(`ChordPilot 和弦分析\n\n${progression}\n\n${details}\n`, 'chordpilot-chords.txt', 'text/plain;charset=utf-8')
}

function exportJson() {
  download(JSON.stringify(props.result, null, 2), 'chordpilot-analysis.json', 'application/json')
}
</script>

<template>
  <section class="export-panel">
    <div class="progression-preview">
      <span>和弦进行</span>
      <strong>{{ chords.map((item) => item.chord).join('  |  ') }}</strong>
    </div>
    <div class="export-actions">
      <Button label="复制和弦" icon="pi pi-copy" @click="emit('copy')" />
      <Button label="导出 TXT" icon="pi pi-file" severity="secondary" outlined @click="exportTxt" />
      <Button label="导出 JSON" icon="pi pi-code" severity="secondary" outlined @click="exportJson" />
      <Button label="分析另一首" icon="pi pi-refresh" severity="contrast" text @click="emit('clear')" />
    </div>
  </section>
</template>
