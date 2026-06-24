<script setup>
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'

defineProps({
  chords: { type: Array, default: () => [] }
})

function formatSeconds(seconds) {
  return `${seconds.toFixed(2)} s`
}

function severity(confidence) {
  if (confidence >= 0.75) return 'success'
  if (confidence >= 0.55) return 'warn'
  return 'danger'
}
</script>

<template>
  <section class="table-section glass-card">
    <div class="section-heading compact">
      <div>
        <span class="eyebrow">DETAILS</span>
        <h2>分析明细</h2>
      </div>
      <span class="result-count">{{ chords.length }} 个片段</span>
    </div>
    <DataTable :value="chords" striped-rows paginator :rows="8" class="chord-table">
      <Column field="start" header="开始">
        <template #body="{ data }">{{ formatSeconds(data.start) }}</template>
      </Column>
      <Column field="end" header="结束">
        <template #body="{ data }">{{ formatSeconds(data.end) }}</template>
      </Column>
      <Column field="chord" header="和弦">
        <template #body="{ data }"><strong class="table-chord">{{ data.chord }}</strong></template>
      </Column>
      <Column field="confidence" header="置信度">
        <template #body="{ data }">
          <Tag :value="`${Math.round(data.confidence * 100)}%`" :severity="severity(data.confidence)" />
        </template>
      </Column>
    </DataTable>
  </section>
</template>
