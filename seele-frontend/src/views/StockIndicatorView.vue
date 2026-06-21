<script setup>
import { reactive, onMounted, onUnmounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from '@/composables/useToast'
import { useStockData } from '@/composables/useStockData'
import { useSyncTask } from '@/composables/useSyncTask'
import { useTableSort } from '@/composables/useTableSort'
import { syncApi, stockIndicatorApi, tradeCalendarApi } from '@/api/stock'
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

const { syncing: taskSyncing, progress: taskProgress, startSync } = useSyncTask()
const syncKey = 'indicator-daily-sync'

const syncProgress = computed(() => {
  const p = taskProgress[syncKey] || { current: 0, total: 0, status: '' }
  const total = p.total || 0
  const current = p.current || 0
  const percent = total ? Math.round(current / total * 100) : 0
  let message = '正在同步数据...'
  if (p.status === 'success') message = '同步完成'
  else if (p.status === 'failed') message = '同步失败'
  return {
    visible: !!taskSyncing[syncKey],
    percent,
    current,
    total,
    message
  }
})

const computing = ref(false)
const computeResult = ref({ visible: false, message: '', tone: 'info' })
let computeResultTimer = null

const { sortField, sortOrder, handleSort } = useTableSort({
  defaultField: 'symbol',
  defaultOrder: 'asc',
  onChange: () => handleSearch()
})

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

async function handleComputeIndicators () {
  if (!filterForm.tradeDate) {
    toast.warning('请选择交易日期')
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
    if (computeResultTimer) clearTimeout(computeResultTimer)
    computeResultTimer = setTimeout(() => {
      computeResult.value.visible = false
    }, 4000)
  }
}

function handleFetchData () {
  if (!filterForm.tradeDate) {
    toast.warning('请选择交易日期')
    return
  }

  startSync(syncKey, () => syncApi.syncByDate(filterForm.tradeDate), {
    confirmMessage: `确定要从API获取 ${filterForm.tradeDate} 的全部A股数据吗？\n同步任务将在后台异步执行，可实时查看进度。`,
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
})

onUnmounted(() => {
  if (computeResultTimer) clearTimeout(computeResultTimer)
})
</script>

<template>
  <div class="stock-indicator page">
    <PageHero
      section="股票日线数据"
      number="03.2"
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
      :fetching="!!taskSyncing[syncKey]"
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

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
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
