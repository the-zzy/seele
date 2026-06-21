<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockDailyApi, tradeCalendarApi } from '@/api/stock'
import { useTableSort } from '@/composables/useTableSort'
import MainwavePickerFilter from '@/components/stock/MainwavePickerFilter.vue'
import MainwaveGroupTable from '@/components/stock/MainwaveGroupTable.vue'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const loading = ref(false)
const groupList = ref([])

const filterForm = ref({
  symbol: '',
  name: '',
  tradeDate: '',
  floatMarketCapMin: 200,
  closeMax: 300,
  avgTurnoverMin: 2,
  avgAmountMin: 2,
  maBull: true
})

const { sortField, sortOrder, handleSort } = useTableSort({
  defaultField: 'score',
  defaultOrder: 'desc',
  getDefaultOrder: field => field === 'score' ? 'desc' : 'asc'
})

async function loadLatestTradeDate () {
  try {
    const date = await tradeCalendarApi.getLatest()
    if (date) {
      filterForm.value.tradeDate = date
      return date
    }
  } catch (error) {
    console.error('获取最近交易日失败:', error)
  }
  filterForm.value.tradeDate = ''
  return ''
}

async function loadData () {
  loading.value = true
  try {
    const params = {
      page_num: 1,
      page_size: 9999,
      sort_field: 'score',
      sort_order: 'desc'
    }
    if (filterForm.value.symbol?.trim()) {
      params.symbol = filterForm.value.symbol.trim()
    }
    if (filterForm.value.name?.trim()) {
      params.name = filterForm.value.name.trim()
    }
    if (filterForm.value.tradeDate) {
      params.trade_date = filterForm.value.tradeDate
    }
    if (filterForm.value.floatMarketCapMin != null) {
      params.float_market_cap_min = filterForm.value.floatMarketCapMin
    }
    if (filterForm.value.closeMax != null) {
      params.close_max = filterForm.value.closeMax
    }
    if (filterForm.value.avgTurnoverMin != null) {
      params.avg_turnover_min = filterForm.value.avgTurnoverMin
    }
    if (filterForm.value.avgAmountMin != null) {
      params.avg_amount_min = filterForm.value.avgAmountMin * 100000000
    }
    if (filterForm.value.maBull) {
      params.ma_bull = true
    }

    const res = await stockDailyApi.getMainwavePicker(params)
    groupList.value = (res?.list || []).map(item => ({
      id: item.id,
      symbol: item.symbol,
      name: item.stock_name || item.name || '-',
      tradeDate: item.trade_date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
      volume: item.volume,
      amount: item.amount,
      amplitude: item.amplitude,
      pctChg: item.pct_chg,
      priceChange: item.price_change,
      turnover: item.turnover,
      ma5: item.ma5,
      ma10: item.ma10,
      ma20: item.ma20,
      ma30: item.ma30,
      ma60: item.ma60,
      volMa5: item.vol_ma5,
      volMa10: item.vol_ma10,
      turnoverMa5: item.turnover_ma5,
      turnoverMa10: item.turnover_ma10,
      chg5d: item.chg_5d,
      chg10d: item.chg_10d,
      netProfit: item.net_profit,
      netProfitYoy: item.net_profit_yoy,
      roe: item.roe,
      score: item.score,
      isHolding: item.is_holding || false,
      layer: item.layer,
      bullDays5: item.bull_days_5,
      bullDays10: item.bull_days_10,
      bullDays20: item.bull_days_20,
      launchDate: item.launch_date,
      launchPctChg: item.launch_pct_chg
    }))
  } catch (error) {
    console.error('加载主升浪分组数据失败:', error)
    groupList.value = []
  } finally {
    loading.value = false
  }
}

async function handleSearch () {
  await loadData()
}

async function handleReset () {
  filterForm.value.symbol = ''
  filterForm.value.name = ''
  filterForm.value.floatMarketCapMin = 200
  filterForm.value.closeMax = 300
  filterForm.value.avgTurnoverMin = 2
  filterForm.value.avgAmountMin = 2
  filterForm.value.maBull = true
  await loadData()
}

function handleRowDblClick (item) {
  if (!item.symbol) return
  router.push({
    name: 'stock-kline',
    params: { symbol: item.symbol },
    query: { name: item.name || '' }
  })
}

onMounted(async () => {
  await loadLatestTradeDate()
  await loadData()
})
</script>

<template>
  <div class="mainwave page">
    <PageHero
      section="选股策略"
      number="08.3"
      title="主升浪分组"
      description="基于交易日期筛选符合主升浪门槛的主板标的，按趋势强度分层分组。双击行跳转K线图。"
      meta="趋势分层"
    />

    <MainwavePickerFilter
      v-model="filterForm"
      @search="handleSearch"
      @reset="handleReset"
    />

    <div
      v-if="!loading && groupList.length === 0 && filterForm.tradeDate"
      class="date-tip"
    >
      {{ filterForm.tradeDate }} 暂无数据，请前往同步任务同步该日期的日线和指标数据
    </div>

    <MainwaveGroupTable
      :list="groupList"
      :loading="loading"
      :sort-field="sortField"
      :sort-order="sortOrder"
      @sort="handleSort"
      @row-dblclick="handleRowDblClick"
    />
  </div>
</template>

<style scoped lang="scss">
.mainwave {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
}

.date-tip {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 4px 10px;
  border-radius: 4px;
  margin: -4px 0 8px;
}
</style>
