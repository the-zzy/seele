<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockDailyApi, tradeCalendarApi } from '@/api/stock'
import { formatNumber } from '@/utils/formatters'
import MainwavePickerFilter from '@/components/stock/MainwavePickerFilter.vue'
import MainwaveTable from '@/components/stock/MainwaveTable.vue'
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

const sortField = ref('symbol')
const sortOrder = ref('asc')

function handleSort (field) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'asc'
  }
  loadData()
}

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
    const params = {
      page_num: pageNum.value,
      page_size: pageSize.value,
      sort_field: sortField.value,
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
    // 如果后端返回了实际使用的交易日期，同步更新前端日期选择器
    if (res?.trade_date) {
      filterForm.tradeDate = res.trade_date
    }
    stockList.value = (res?.list || []).map(item => ({
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
      roe: item.roe
    }))
    total.value = res?.total || 0
  } catch (error) {
    console.error('加载主升浪选股数据失败:', error)
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
  sortField.value = 'symbol'
  sortOrder.value = 'asc'
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
  <div class="stock-basic page">
    <PageHero
      section="选股策略"
      number="03.7"
      title="主升浪选股"
      description="基于交易日期筛选符合主升浪门槛的主板标的：流通市值≥200亿、股价≤300元、10日换手≥2%、10日成交额≥2亿。双击行跳转K线图。"
      meta="选股门槛"
    />

    <MainwavePickerFilter
      v-model="filterForm"
      @search="handleSearch"
      @reset="handleReset"
    />

    <MainwaveTable
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
.stock-basic {
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
