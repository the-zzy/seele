<script setup>
import { reactive, onMounted } from 'vue'
import { getLatestTradeDate } from '@/utils/date'

const emit = defineEmits(['search'])

const form = reactive({
  tradeDate: '',
  minPctChg: 2.0,
  maxPctChg: 8.0,
  minTurnover: 2.0,
  minAmount: 200000000,
  maAlignment: true,
  macdGoldenCross: false,
  rsiMin: 40,
  rsiMax: 80,
  volumeRatio: 1.5,
  excludeSt: true,
  excludeCyb: true,
  excludeKcb: true,
  excludeBse: true
})

function buildPayload () {
  return {
    trade_date: form.tradeDate,
    min_pct_chg: form.minPctChg,
    max_pct_chg: form.maxPctChg,
    min_turnover: form.minTurnover,
    min_amount: form.minAmount,
    ma_alignment: form.maAlignment,
    macd_golden_cross: form.macdGoldenCross,
    rsi_min: form.rsiMin,
    rsi_max: form.rsiMax,
    volume_ratio: form.volumeRatio,
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
      <label>涨幅下限 %</label>
      <input v-model.number="form.minPctChg" type="number" step="0.1" />
    </div>
    <div class="filter-item">
      <label>涨幅上限 %</label>
      <input v-model.number="form.maxPctChg" type="number" step="0.1" />
    </div>
    <div class="filter-item">
      <label>最低换手率 %</label>
      <input v-model.number="form.minTurnover" type="number" step="0.1" />
    </div>
    <div class="filter-item">
      <label>10日成交额下限</label>
      <input v-model.number="form.minAmount" type="number" step="10000000" />
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
      <label>量比阈值</label>
      <input v-model.number="form.volumeRatio" type="number" step="0.1" />
    </div>
    <div class="filter-row">
      <label class="checkbox-label">
        <input v-model="form.maAlignment" type="checkbox" />
        均线多头排列
      </label>
      <label class="checkbox-label">
        <input v-model="form.macdGoldenCross" type="checkbox" />
        MACD金叉
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
