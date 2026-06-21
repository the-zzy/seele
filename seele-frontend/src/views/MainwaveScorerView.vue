<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockDailyApi, tradeCalendarApi } from '@/api/stock'
import { useTableSort } from '@/composables/useTableSort'
import MainwavePickerFilter from '@/components/stock/MainwavePickerFilter.vue'
import MainwaveScoreTable from '@/components/stock/MainwaveScoreTable.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const loading = ref(false)
const stockList = ref([])
const total = ref(0)
const pageNum = ref(1)
const pageSize = ref(10)

let filterForm = reactive({
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
  getDefaultOrder: field => field === 'score' ? 'desc' : 'asc',
  onChange: () => loadData()
})

async function loadLatestTradeDate () {
  try {
    const date = await tradeCalendarApi.getLatest()
    if (date) {
      filterForm.tradeDate = date
      return date
    }
  } catch (error) {
    console.error('获取最近交易日失败:', error)
  }
  filterForm.tradeDate = ''
  return ''
}

async function loadData () {
  loading.value = true
  try {
    const sortKeyBackendMap = {
      trendScore: 'trend_score',
      strengthScore: 'strength_score',
      momentumScore: 'momentum_score'
    }

    const params = {
      page_num: pageNum.value,
      page_size: pageSize.value,
      sort_field: sortKeyBackendMap[sortField.value] || sortField.value,
      sort_order: sortOrder.value
    }
    if (filterForm.symbol?.trim()) {
      params.symbol = filterForm.symbol.trim()
    }
    if (filterForm.name?.trim()) {
      params.name = filterForm.name.trim()
    }
    if (filterForm.tradeDate) {
      params.trade_date = filterForm.tradeDate
    }
    if (filterForm.floatMarketCapMin != null) {
      params.float_market_cap_min = filterForm.floatMarketCapMin
    }
    if (filterForm.closeMax != null) {
      params.close_max = filterForm.closeMax
    }
    if (filterForm.avgTurnoverMin != null) {
      params.avg_turnover_min = filterForm.avgTurnoverMin
    }
    if (filterForm.avgAmountMin != null) {
      params.avg_amount_min = filterForm.avgAmountMin * 100000000
    }
    if (filterForm.maBull) {
      params.ma_bull = true
    }

    const res = await stockDailyApi.getMainwavePicker(params)
    if (res?.trade_date) {
      filterForm.tradeDate = res.trade_date
    }
    stockList.value = (res?.list || []).map(item => ({
      id: item.id,
      symbol: item.symbol,
      name: item.stock_name || item.name || '-',
      tradeDate: item.trade_date,
      close: item.close,
      pctChg: item.pct_chg,
      chg5d: item.chg_5d,
      chg10d: item.chg_10d,
      ma5: item.ma5,
      netProfitYoy: item.net_profit_yoy,
      roe: item.roe,
      floatMarketCap: item.float_market_cap,
      turnoverMa10: item.turnover_ma10,
      score: item.score || null,
      isHolding: item.is_holding || false
    }))
    total.value = res?.total || 0
  } catch (error) {
    console.error('加载主升浪评分数据失败:', error)
    stockList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleSearch () {
  pageNum.value = 1
  await loadData()
}

async function handleReset () {
  filterForm.symbol = ''
  filterForm.name = ''
  filterForm.floatMarketCapMin = 200
  filterForm.closeMax = 300
  filterForm.avgTurnoverMin = 2
  filterForm.avgAmountMin = 2
  filterForm.maBull = true
  sortField.value = 'score'
  sortOrder.value = 'desc'
  pageNum.value = 1
  await loadData()
}

async function handlePageChange (newPage) {
  pageNum.value = newPage
  await loadData()
}

async function handlePageSizeChange (newSize) {
  pageSize.value = newSize
  pageNum.value = 1
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
  <div class="scorer-page page">
    <PageHero
      section="选股策略"
      number="08.2"
      title="主升浪评分"
      description="对主升浪选股结果进行多维度评分：趋势形态、方向分散、板块强度、业绩质量、市值流动性、催化剂。满分100分，60分及格，80分强烈推荐。"
      meta="评分体系"
    />

    <MainwavePickerFilter
      v-model="filterForm"
      :live-loading="false"
      @search="handleSearch"
      @reset="handleReset"
      @fetch-live="() => {}"
    />

    <MainwaveScoreTable
      :list="stockList"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :loading="loading"
      @sort="handleSort"
      @row-dblclick="handleRowDblClick"
    />

    <BasePagination
      v-if="total > 0"
      :page-num="pageNum"
      :page-size="pageSize"
      :total="total"
      @update:page-num="handlePageChange"
      @update:page-size="handlePageSizeChange"
    />
  </div>
</template>

<style scoped lang="scss">
.scorer-page {
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
</style>
