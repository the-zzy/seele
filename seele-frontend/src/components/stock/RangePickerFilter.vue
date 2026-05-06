<script setup>
import { reactive, onMounted } from 'vue'
import { getLatestTradeDate } from '@/utils/date'

const emit = defineEmits(['search'])

const form = reactive({
  tradeDate: '',
  maxPctChg20d: 10.0,
  minAmplitude20d: 3.0,
  bbWidthMax: 0.08,
  rsiMin: 35,
  rsiMax: 65,
  volumeShrink: true,
  nearMa20: true,
  minAmount: 200000000,
  excludeSt: true,
  excludeCyb: true,
  excludeKcb: true,
  excludeBse: true
})

function buildPayload () {
  return {
    trade_date: form.tradeDate,
    max_pct_chg_20d: form.maxPctChg20d,
    min_amplitude_20d: form.minAmplitude20d,
    bb_width_max: form.bbWidthMax,
    rsi_min: form.rsiMin,
    rsi_max: form.rsiMax,
    volume_shrink: form.volumeShrink,
    near_ma20: form.nearMa20,
    min_amount: form.minAmount,
    exclude_st: form.excludeSt,
    exclude_cyb: form.excludeCyb,
    exclude_kcb: form.excludeKcb,
    exclude_bse: form.excludeBse
  }
}

function handleSearch () {
  emit('search', buildPayload())
}

onMounted(async () => {
  form.tradeDate = await getLatestTradeDate()
  emit('search', buildPayload())
})
</script>

<template>
  <div class="filter-section">
    <div class="filter-item">
      <label>交易日期</label>
      <input v-model="form.tradeDate" type="date" />
    </div>
    <div class="filter-item">
      <label>20日涨幅上限 %</label>
      <input v-model.number="form.maxPctChg20d" type="number" step="0.1" />
    </div>
    <div class="filter-item">
      <label>20日振幅下限 %</label>
      <input v-model.number="form.minAmplitude20d" type="number" step="0.1" />
    </div>
    <div class="filter-item">
      <label>布林带宽上限</label>
      <input v-model.number="form.bbWidthMax" type="number" step="0.01" />
    </div>
    <div class="filter-item">
      <label>RSI 下限</label>
      <input v-model.number="form.rsiMin" type="number" step="1" />
    </div>
    <div class="filter-item">
      <label>RSI 上限</label>
      <input v-model.number="form.rsiMax" type="number" step="1" />
    </div>
    <div class="filter-item">
      <label>10日成交额下限</label>
      <input v-model.number="form.minAmount" type="number" step="10000000" />
    </div>
    <div class="filter-row">
      <label class="checkbox-label">
        <input v-model="form.volumeShrink" type="checkbox" />
        近期缩量
      </label>
      <label class="checkbox-label">
        <input v-model="form.nearMa20" type="checkbox" />
        收盘价靠近MA20
      </label>
      <label class="checkbox-label">
        <input v-model="form.excludeSt" type="checkbox" />
        排除ST
      </label>
      <label class="checkbox-label">
        <input v-model="form.excludeCyb" type="checkbox" />
        排除创业板
      </label>
      <label class="checkbox-label">
        <input v-model="form.excludeKcb" type="checkbox" />
        排除科创板
      </label>
      <label class="checkbox-label">
        <input v-model="form.excludeBse" type="checkbox" />
        排除北交所
      </label>
    </div>
    <div class="filter-actions">
      <button class="btn-primary" @click="handleSearch">查询</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';
</style>
