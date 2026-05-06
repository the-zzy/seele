<script setup>
import { reactive, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStockData } from '@/composables/useStockData'
import { stockDailyApi, syncApi } from '@/api/stock'
import { getDefaultDate } from '@/utils/date'
import StockFilterPanel from '@/components/stock/StockFilterPanel.vue'
import StockDataTable from '@/components/stock/StockDataTable.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SyncProgress from '@/components/common/SyncProgress.vue'
import PageHero from '@/components/common/PageHero.vue'

const {
  loading,
  stockList,
  total,
  pageNum,
  pageSize,
  setPage,
  setPageSize,
  clearCache
} = useStockData()

// eslint-disable-next-line prefer-const
let filterForm = reactive({
  tradeDate: '',
  symbol: '',
  excludeSt: true,
  excludeCyb: true,
  excludeKcb: true,
  excludeBse: true
})

const latestTradeDate = ref('')
const router = useRouter()

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

async function loadLatestTradeDate () {
  try {
    const dates = await stockDailyApi.getTradeDates()
    if (Array.isArray(dates) && dates.length > 0) {
      const latestDate = dates[0]
      latestTradeDate.value = latestDate
      filterForm.tradeDate = latestDate
      return latestDate
    }
  } catch (error) {
    console.error('获取最近交易日失败:', error)
  }
  const today = getDefaultDate()
  filterForm.tradeDate = today
  latestTradeDate.value = today
  return today
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

async function handleSearch () {
  clearCache()
  await setPage(1, getQueryParams())
}

async function handleReset () {
  filterForm.tradeDate = latestTradeDate.value || ''
  filterForm.symbol = ''
  filterForm.excludeSt = true
  filterForm.excludeCyb = true
  filterForm.excludeKcb = true
  filterForm.excludeBse = true
  sortField.value = 'symbol'
  sortOrder.value = 'asc'
  await setPage(1, getQueryParams())
}

async function handlePageChange (newPage) {
  await setPage(newPage, getQueryParams())
}

async function handlePageSizeChange (newSize) {
  await setPageSize(newSize, getQueryParams())
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
        clearCache()
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
  const date = await loadLatestTradeDate()
  if (date) {
    await handleSearch()
  }
})
</script>

<template>
  <div class="stock-list page">
    <PageHero
      section="股票日线数据"
      number="02.1"
      title="基本数据"
      description="按交易日期检索全市场基础日线行情：开高低收、涨跌、成交。指标列在「指标数据」中独立维护。"
      meta="行情快照"
    />

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
.stock-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;
}
</style>
