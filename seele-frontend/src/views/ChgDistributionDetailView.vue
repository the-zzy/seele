<script setup>
import { reactive, computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { stockDailyApi, syncApi } from '@/api/stock'
import { getLatestTradeDate } from '@/utils/date'
import StockFilterPanel from '@/components/stock/StockFilterPanel.vue'
import StockDataTable from '@/components/stock/StockDataTable.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SyncProgress from '@/components/common/SyncProgress.vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const stockList = ref([])
const total = ref(0)
const pageNum = ref(1)
const pageSize = ref(100)
// totalPages removed; BasePagination computes internally
const sortedStockList = computed(() => stockList.value || [])

const cacheKey = ref(null)
const cachedList = ref([])

const syncing = ref(false)
const syncProgress = ref({
  visible: false,
  percent: 0,
  current: 0,
  total: 0,
  message: ''
})
let syncEventSource = null

const sortField = ref('symbol')
const sortOrder = ref('asc')

// eslint-disable-next-line prefer-const
let filterForm = reactive({
  tradeDate: '',
  symbol: '',
  excludeSt: true,
  excludeCyb: true,
  excludeKcb: true,
  excludeBse: true
})

const tradeDate = computed(() => filterForm.tradeDate || '')

function buildCacheKey (params) {
  return JSON.stringify({
    tradeDate: params.tradeDate,
    excludeSt: params.excludeSt,
    excludeCyb: params.excludeCyb,
    excludeKcb: params.excludeKcb,
    excludeBse: params.excludeBse,
    symbol: params.symbol
  })
}

function compareForSort (a, b) {
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  if (typeof a === 'number' && typeof b === 'number') {
    return a - b
  }
  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

function handleSort (field) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'asc'
  }
  handleSearch()
}

function handleRowDblClick (item) {
  if (!item.symbol) return
  router.push({
    name: 'stock-kline',
    params: { symbol: item.symbol },
    query: { name: item.name || '' }
  })
}

function goBack () {
  router.push({ name: 'chg-distribution' })
}

function getQueryParams () {
  const params = {}
  if (filterForm.tradeDate) {
    params.tradeDate = filterForm.tradeDate
  }
  const trimmedSymbol = filterForm.symbol?.trim()
  if (trimmedSymbol) {
    params.symbol = trimmedSymbol
  }
  params.excludeSt = filterForm.excludeSt
  params.excludeCyb = filterForm.excludeCyb
  params.excludeKcb = filterForm.excludeKcb
  params.excludeBse = filterForm.excludeBse
  params.sortField = sortField.value
  params.sortOrder = sortOrder.value
  return params
}

async function loadStockData (params = {}) {
  loading.value = true
  try {
    if (!params.tradeDate) {
      stockList.value = []
      total.value = 0
      return
    }

    const currentKey = buildCacheKey(params)
    let list = cachedList.value

    if (cacheKey.value !== currentKey) {
      const data = await stockDailyApi.getAllByTradeDate(params.tradeDate, {
        exclude_st: params.excludeSt || false,
        exclude_cyb: params.excludeCyb || false,
        exclude_kcb: params.excludeKcb || false,
        exclude_bse: params.excludeBse || false
      })
      list = (data?.list || []).map(item => ({
        id: item.id,
        symbol: item.symbol,
        name: item.stock_name || item.name || '-',
        area: item.area || '-',
        industry: item.industry || '-',
        market: item.market || '-',
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
        turnover: item.turnover
      }))

      if (params.excludeSt) {
        list = list.filter(item => !item.name?.includes('ST'))
      }
      if (params.excludeCyb) {
        list = list.filter(item =>
          !item.symbol?.startsWith('300') &&
          !item.symbol?.startsWith('301')
        )
      }
      if (params.excludeKcb) {
        list = list.filter(item =>
          !item.symbol?.startsWith('688') &&
          !item.symbol?.startsWith('689')
        )
      }
      if (params.excludeBse) {
        list = list.filter(item =>
          !item.symbol?.startsWith('4') &&
          !item.symbol?.startsWith('8')
        )
      }

      if (params.symbol) {
        const symbolFilter = params.symbol.trim()
        list = list.filter(item =>
          item.symbol?.includes(symbolFilter) ||
          item.name?.includes(symbolFilter)
        )
      }

      list = list.filter(item => item.pctChg > 2)

      cachedList.value = list
      cacheKey.value = currentKey
    }

    const sf = params.sortField || 'symbol'
    const so = params.sortOrder || 'asc'
    list.sort((a, b) => {
      const result = compareForSort(a[sf], b[sf])
      return so === 'asc' ? result : -result
    })

    total.value = list.length
    const start = (pageNum.value - 1) * pageSize.value
    const end = start + pageSize.value
    stockList.value = list.slice(start, end)
  } catch (error) {
    console.error('加载股票数据失败:', error)
    stockList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleSearch () {
  pageNum.value = 1
  cacheKey.value = null
  cachedList.value = []
  await loadStockData(getQueryParams())
}

async function handleReset () {
  filterForm.symbol = ''
  filterForm.excludeSt = true
  filterForm.excludeCyb = true
  filterForm.excludeKcb = true
  filterForm.excludeBse = true
  sortField.value = 'symbol'
  sortOrder.value = 'asc'
  pageNum.value = 1
  await loadStockData(getQueryParams())
}

async function handlePageChange (newPage) {
  pageNum.value = newPage
  await loadStockData(getQueryParams())
}

async function handlePageSizeChange (newSize) {
  pageSize.value = newSize
  pageNum.value = 1
  await loadStockData(getQueryParams())
}

function handleFetchData () {
  if (!filterForm.tradeDate) {
    alert('请选择交易日期')
    return
  }

  if (!confirm(`确定要从API获取 ${filterForm.tradeDate} 的全部A股数据吗？\n同步任务将在后台异步执行，可实时查看进度。`)) {
    return
  }

  if (syncEventSource) {
    syncEventSource.close()
    syncEventSource = null
  }

  syncing.value = true
  syncProgress.value = {
    visible: true,
    percent: 0,
    current: 0,
    total: 0,
    message: '正在连接...'
  }

  const es = syncApi.createSyncStream(filterForm.tradeDate)
  syncEventSource = es

  es.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      if (payload.status === 'running') {
        const current = payload.current || 0
        const total = payload.total || 0
        syncProgress.value = {
          visible: true,
          percent: total ? Math.round(current / total * 100) : 0,
          current,
          total,
          message: payload.symbol
            ? `正在同步: ${payload.symbol}`
            : '正在同步数据...'
        }
      } else if (payload.status === 'completed') {
        const result = payload.result || {}
        syncProgress.value = {
          visible: true,
          percent: 100,
          current: result.upserted || 0,
          total: result.total_stocks || 0,
          message: result.summary || '同步完成'
        }
        es.close()
        syncEventSource = null
        syncing.value = false
        cacheKey.value = null
        cachedList.value = []
        handleSearch()
        setTimeout(() => {
          syncProgress.value.visible = false
        }, 3000)
      } else if (payload.status === 'failed') {
        syncProgress.value = {
          visible: true,
          percent: 0,
          current: 0,
          total: 0,
          message: '同步失败: ' + (payload.error || '未知错误')
        }
        es.close()
        syncEventSource = null
        syncing.value = false
      }
    } catch (e) {
      console.error('解析进度消息失败:', e)
    }
  }

  es.onerror = () => {
    syncProgress.value.message = '连接异常，请刷新页面查看结果'
    es.close()
    syncEventSource = null
    syncing.value = false
  }
}

onMounted(async () => {
  let date = route.query.date
  if (!date) {
    date = await getLatestTradeDate()
  }
  filterForm.tradeDate = date
  await handleSearch()
})
</script>

<template>
  <div class="chg-distribution-detail page">
    <div class="detail-bar">
      <button class="back-btn" @click="goBack">
        <span class="arrow">←</span>
        <span>涨幅分布统计</span>
      </button>
      <span class="bar-divider" />
      <div class="bar-meta">
        <span class="bar-label">交易日</span>
        <span class="bar-date">{{ tradeDate }}</span>
        <span class="bar-count">{{ total }} 只入选</span>
      </div>
    </div>

    <StockFilterPanel
      v-model="filterForm"
      show-fetch
      :fetching="syncing"
      @search="handleSearch"
      @reset="handleReset"
      @fetch="handleFetchData"
    />

    <SyncProgress
      :visible="syncProgress.visible"
      :percent="syncProgress.percent"
      :current="syncProgress.current"
      :total="syncProgress.total"
      :message="syncProgress.message"
    />

    <StockDataTable
      :list="sortedStockList"
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
.chg-distribution-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;
}

.detail-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 0 14px;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 8px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 7px 12px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  transition: all 0.2s;

  .arrow { font-size: 13px; }

  &:hover {
    color: var(--text-primary);
    border-color: var(--text-faint);
  }
}

.bar-divider {
  width: 1px;
  height: 18px;
  background: var(--rule);
}

.bar-meta {
  display: flex;
  align-items: baseline;
  gap: 12px;

  .bar-label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .bar-date {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: 0;
  }

  .bar-count {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--accent);
    letter-spacing: 0.06em;
    margin-left: 4px;
  }
}
</style>
