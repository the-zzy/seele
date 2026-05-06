<script setup>
import { reactive, onMounted } from 'vue'

const emit = defineEmits(['search'])

const form = reactive({
  minDays: 2,
  maxDays: null,
  lookback: 30
})

function buildPayload () {
  const payload = {
    min_days: form.minDays,
    lookback: form.lookback
  }
  if (form.maxDays != null && form.maxDays !== '') {
    payload.max_days = form.maxDays
  }
  return payload
}

function handleSearch () {
  emit('search', buildPayload())
}

onMounted(() => {
  emit('search', buildPayload())
})
</script>

<template>
  <div class="filter-section">
    <div class="filter-item">
      <label>最小连续缩量天数</label>
      <input v-model.number="form.minDays" type="number" min="1" />
    </div>
    <div class="filter-item">
      <label>最大连续缩量天数</label>
      <input v-model.number="form.maxDays" type="number" min="1" placeholder="不限" />
    </div>
    <div class="filter-item">
      <label>历史交易日数量</label>
      <input v-model.number="form.lookback" type="number" min="10" max="120" />
    </div>
    <div class="filter-actions">
      <button class="btn-primary" @click="handleSearch">查询</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';
</style>
