<script setup>
import { reactive, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStockData } from '@/composables/useStockData'
import { stockDailyApi, syncApi, stockIndicatorApi } from '@/api/stock'
import { getDefaultDate } from '@/utils/date'
import StockFilterPanel from '@/components/stock/StockFilterPanel.vue'
import StockIndicatorTable from '@/components/stock/StockIndicatorTable.vue'
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

const computing = ref(false)
const computeResult = ref({ visible: false, message: '', tone: 'info' })

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

async function handleComputeIndicators () {
  if (!filterForm.tradeDate) {
    alert('请选择交易日期')
    return
  }

  if (!confirm(`确定要计算 ${filterForm.tradeDate} 的日线指标吗？`)) {
    return
  }

  computing.value = true
  computeResult.value = { visible: true, message: '指标正在计算...', tone: 'info' }

  try {
    const res = await stockIndicatorApi.compute(filterForm.tradeDate)
    const data = res || {}
    computeResult.value = {
      visible: true,
      tone: 'success',
      message: `计算完成 — 总 ${data.total || 0} · 成功 ${data.success || 0} · 失败 ${data.failed || 0}`
    }
    clearCache()
    await handleSearch()
  } catch (error) {
    computeResult.value = {
      visible: true,
      tone: 'error',
      message: '计算失败: ' + (error?.response?.data?.message || error.message || '未知错误')
    }
  } finally {
    computing.value = false
    setTimeout(() => {
      computeResult.value.visible = false
    }, 4000)
  }
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
  <div class="stock-indicator page">
    <PageHero
      section="股票日线数据"
      number="02.2"
      title="指标数据"
      description="均线、均量、均换手等衍生指标。基于已同步的日线行情批量计算并落库。"
      meta="衍生指标"
    >
      <template #actions>
        <button
          class="btn-compute"
          :disabled="computing"
          @click="handleComputeIndicators"
        >
          <span class="btn-dot" :class="{ active: computing }" />
          {{ computing ? '计算中…' : '计算指标' }}
        </button>
      </template>
    </PageHero>

    <StockFilterPanel
      v-model="filterForm"
      show-fetch
      :fetching="syncing"
      @search="handleSearch"
      @reset="handleReset"
      @fetch="handleFetchData"
    />

    <transition name="fade">
      <div
        v-if="computeResult.visible"
        class="compute-toast"
        :class="`tone-${computeResult.tone}`"
      >
        <span class="toast-tag">{{ computeResult.tone === 'error' ? '错误' : computeResult.tone === 'success' ? '完成' : '运行中' }}</span>
        <span class="toast-msg">{{ computeResult.message }}</span>
      </div>
    </transition>

    <SyncProgress
      :visible="syncProgress.visible"
      :percent="syncProgress.percent"
      :current="syncProgress.current"
      :total="syncProgress.total"
      :message="syncProgress.message"
    />

    <StockIndicatorTable
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
.stock-indicator {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;
}

.btn-compute {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  background: var(--text-primary);
  color: var(--bg-primary);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: transform 0.15s ease, opacity 0.15s ease, background 0.2s;

  .btn-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);

    &.active {
      animation: pulse 1.2s ease-in-out infinite;
    }
  }

  &:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.compute-toast {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 4px;
  border: 1px solid var(--rule);
  background: var(--bg-secondary);
  font-size: 12px;
  color: var(--text-secondary);

  .toast-tag {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 2px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
  }

  &.tone-success {
    border-color: rgba(82, 196, 26, 0.25);
    .toast-tag { background: rgba(82, 196, 26, 0.12); color: var(--down); }
  }

  &.tone-error {
    border-color: rgba(255, 77, 79, 0.25);
    .toast-tag { background: rgba(255, 77, 79, 0.12); color: var(--up); }
  }

  &.tone-info .toast-tag {
    color: var(--accent);
    background: var(--accent-subtle);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
