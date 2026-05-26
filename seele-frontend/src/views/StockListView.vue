<script setup>
import { reactive, onMounted, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from '@/composables/useToast'
import { useStockData } from '@/composables/useStockData'
import { useSyncTask } from '@/composables/useSyncTask'
import { syncApi, tradeCalendarApi } from '@/api/stock'
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

const { syncing: syncMap, progress: taskProgress, startSync, restoreTasks } = useSyncTask()

const syncKey = computed(() => {
  const d = filterForm.tradeDate?.replace(/-/g, '')
  return d ? 'daily_' + d : 'daily_unknown'
})

const syncing = computed(() => !!syncMap[syncKey.value])
const syncProgress = computed(() => {
  const p = taskProgress[syncKey.value] || { current: 0, total: 0, status: '' }
  const current = p.current || 0
  const total = p.total || 0
  const percent = total ? Math.round(current / total * 100) : 0

  if (p.status === 'success') {
    return { visible: true, percent: 100, current, total, message: '同步完成' }
  }
  if (p.status === 'failed') {
    return { visible: true, percent: 0, current: 0, total: 0, message: '同步失败' }
  }
  if (p.status === 'running') {
    return { visible: true, percent, current, total, message: `正在同步: ${current} / ${total}` }
  }
  return { visible: false, percent: 0, current: 0, total: 0, message: '' }
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
    const date = await tradeCalendarApi.getLatest()
    if (date) {
      filterForm.tradeDate = date
      latestTradeDate.value = date
      return date
    }
  } catch (error) {
    console.error('获取最近交易日失败:', error)
  }
  filterForm.tradeDate = ''
  latestTradeDate.value = ''
  return ''
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

async function handleFetchData () {
  if (!filterForm.tradeDate) {
    toast.warning('请选择交易日期')
    return
  }

  const tradeDateFormatted = filterForm.tradeDate.replace(/-/g, '')

  await startSync(syncKey.value, () => syncApi.syncByDate(filterForm.tradeDate), {
    confirmMessage: `确定要从API获取 ${filterForm.tradeDate} 的全部A股数据吗？\n同步任务将在后台异步执行，可实时查看进度。`,
    existingMatcher: t => t.job_type === 'daily' && t.trade_date === tradeDateFormatted,
    interval: 3000,
    onDone: (data) => {
      if (data?.status === 'success') {
        clearCache()
        handleSearch()
      }
    }
  })
}

onMounted(async () => {
  const date = await loadLatestTradeDate()
  if (date) {
    await handleSearch()
  }

  // 刷新后自动恢复正在运行的同步任务跟踪
  const tradeDateFormatted = filterForm.tradeDate?.replace(/-/g, '')
  await restoreTasks([
    t => t.job_type === 'daily' && t.trade_date === tradeDateFormatted ? syncKey.value : null
  ], {
    interval: 3000,
    onDone: (data) => {
      if (data?.status === 'success') {
        clearCache()
        handleSearch()
      }
    }
  })
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

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
}
</style>
