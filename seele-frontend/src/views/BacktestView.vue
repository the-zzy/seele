<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { backtestApi } from '@/api/backtest'
import { stockDailyApi } from '@/api/stock'
import { toast } from '@/composables/useToast'
import { useEChart } from '@/composables/useEChart'
import { useTableSort } from '@/composables/useTableSort'
import PageHero from '@/components/common/PageHero.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import BacktestStatsCards from '@/components/backtest/BacktestStatsCards.vue'
import BacktestTradeTable from '@/components/backtest/BacktestTradeTable.vue'
import BacktestPositionTable from '@/components/backtest/BacktestPositionTable.vue'
import BacktestPoolTable from '@/components/backtest/BacktestPoolTable.vue'

const run = ref(null)
const snapshots = ref([])
const trades = ref([])
const decisions = ref([])
const pool = ref([])
const reasoning = ref('')
const loading = ref(false)
const stepLoading = ref(false)
const autoRunning = ref(false)
const activeTab = ref('positions')
const showDeleteConfirm = ref(false)
const showClearAllConfirm = ref(false)
const runList = ref([])
const selectedRunId = ref(null)

const form = ref({
  startDate: '',
  endDate: '',
  initialCapital: 40000,
  aiModel: 'deepseek-v4-pro'
})

const tradeSort = useTableSort({ defaultField: 'trade_date', defaultOrder: 'desc' })
const positionSort = useTableSort({ defaultField: 'symbol', defaultOrder: 'asc' })
const poolSort = useTableSort({ defaultField: 'score', defaultOrder: 'desc' })

const trendRef = useEChart()
const dailyPnlRef = useEChart()

const latestSnapshot = computed(() => {
  return snapshots.value.length ? snapshots.value[snapshots.value.length - 1] : null
})

function calcPositions (tradeList) {
  const pos = {}
  // 必须按时间正序计算，否则先遇到卖出会导致持仓被错误重建
  const sorted = [...tradeList].sort((a, b) => {
    if (a.trade_date !== b.trade_date) {
      return a.trade_date.localeCompare(b.trade_date)
    }
    return (a.id || 0) - (b.id || 0)
  })
  for (const t of sorted) {
    const symbol = t.symbol
    if (!pos[symbol]) {
      pos[symbol] = { symbol, name: t.name, quantity: 0, cost: 0 }
    }
    const qty = Number(t.quantity)
    const amount = Number(t.amount)
    if (t.trade_type === 'BUY') {
      pos[symbol].quantity += qty
      pos[symbol].cost += amount
    } else {
      const oldQty = pos[symbol].quantity
      pos[symbol].quantity -= qty
      if (oldQty > 0) {
        pos[symbol].cost -= pos[symbol].cost * (qty / oldQty)
      }
      if (pos[symbol].quantity <= 0) {
        delete pos[symbol]
      }
    }
  }
  for (const p of Object.values(pos)) {
    p.avg_cost = p.quantity > 0 ? p.cost / p.quantity : 0
  }
  return pos
}

const positions = computed(() => calcPositions(trades.value))
const closeMap = ref({})

function setCloseMapFromPool (poolList) {
  const map = {}
  for (const s of poolList || []) {
    if (s.close != null) map[s.symbol] = Number(s.close)
  }
  closeMap.value = map
}

async function loadHoldingCloses (symbols, tradeDate) {
  if (!symbols.length || !tradeDate) return
  try {
    const data = await stockDailyApi.getCloseByDate(symbols.join(','), tradeDate)
    const map = { ...closeMap.value }
    for (const symbol of symbols) {
      if (data?.[symbol]?.close != null) {
        map[symbol] = Number(data[symbol].close)
      }
    }
    closeMap.value = map
  } catch (e) {
    console.error('加载持仓收盘价失败:', e)
  }
}

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function getThemeColor (name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#999'
}

function resumeStepTask (taskId) {
  stepLoading.value = true
  startTaskPoll(
    taskId,
    {
      onSuccess: async (result) => {
        try {
          run.value = result.run
          snapshots.value.push(result.snapshot)
          trades.value = [...trades.value, ...result.trades]
          pool.value = result.pool || []
          setCloseMapFromPool(pool.value)
          reasoning.value = result.reasoning || ''
          // 重新拉取完整数据（包含 decisions、最新收盘价等）
          await loadRun(run.value.id)
          renderCharts()
          toast.success(`已推进到 ${result.run.current_date}`)
        } catch (inner) {
          console.error('步进成功但刷新页面数据失败:', inner)
          toast.error('步进成功但页面刷新失败，请手动刷新')
        } finally {
          stepLoading.value = false
        }
      },
      onFailed: (err) => {
        toast.error('步进失败: ' + err)
        stepLoading.value = false
      },
      onPollError: (err) => {
        toast.warning('AI 仍在运行，请勿重复点击（' + err + '）')
      }
    }
  )
}

async function loadRun (runId) {
  loading.value = true
  try {
    const [runRes, snapshotRes, tradeRes, decisionRes] = await Promise.all([
      backtestApi.getById(runId),
      backtestApi.getSnapshots(runId),
      backtestApi.getTrades(runId),
      backtestApi.getDecisions(runId)
    ])
    run.value = runRes
    snapshots.value = snapshotRes?.list || []
    trades.value = tradeRes?.list || []
    decisions.value = decisionRes?.list || []

    // 刷新页面后 pool 为空，需单独拉取持仓股的收盘价
    const posSymbols = Object.keys(calcPositions(trades.value))
    if (posSymbols.length && runRes?.current_date) {
      await loadHoldingCloses(posSymbols, runRes.current_date)
    }

    // 如果当前 run 有进行中的后台任务，恢复轮询
    if (runRes?.status === 'running') {
      try {
        const runningTask = await backtestApi.getRunningTask(runId)
        if (runningTask?.task_id) {
          resumeStepTask(runningTask.task_id)
        }
      } catch (e) {
        console.error('查询运行中任务失败:', e)
      }
    }
  } catch (e) {
    toast.error('加载回测失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

let pollTimer = null
function startPoll (taskId) {
  clearInterval(pollTimer)
  const doPoll = async () => {
    try {
      const data = await backtestApi.getTaskStatus(taskId)
      if (data.status === 'success' || data.status === 'failed') {
        clearInterval(pollTimer)
        autoRunning.value = false
        await loadRun(run.value.id)
        if (data.status === 'failed') {
          toast.error('自动运行失败: ' + (data.error || '未知错误'))
        } else {
          toast.success('自动运行完成')
        }
      }
    } catch (e) {
      if (e.response?.status === 404) {
        clearInterval(pollTimer)
        autoRunning.value = false
      }
    }
  }
  doPoll()
  pollTimer = setInterval(doPoll, 2000)
}

function startTaskPoll (taskId, { onSuccess, onFailed, onPollError }) {
  clearInterval(pollTimer)
  const doPoll = async () => {
    try {
      const data = await backtestApi.getTaskStatus(taskId)
      if (data.status === 'success') {
        clearInterval(pollTimer)
        onSuccess(data.result)
      } else if (data.status === 'failed') {
        clearInterval(pollTimer)
        onFailed(data.error || '任务失败')
      }
      // running 状态继续轮询
    } catch (e) {
      clearInterval(pollTimer)
      if (e.response?.status === 404) {
        onPollError('任务不存在')
      } else {
        onPollError(e.message || '轮询任务状态失败')
      }
    }
  }
  doPoll()
  pollTimer = setInterval(doPoll, 2000)
}

async function onCreate () {
  if (!form.value.startDate) {
    toast.warning('请选择开始日期')
    return
  }
  loading.value = true
  try {
    const { task_id: taskId } = await backtestApi.create({
      start_date: form.value.startDate,
      end_date: form.value.endDate || undefined,
      initial_capital: form.value.initialCapital,
      ai_model: form.value.aiModel
    })
    startTaskPoll(
      taskId,
      {
        onSuccess: async (result) => {
          run.value = result.run
          selectedRunId.value = result.run.id
          snapshots.value = result.snapshot ? [result.snapshot] : []
          trades.value = result.trades || []
          pool.value = result.pool || []
          setCloseMapFromPool(pool.value)
          const currentDate = result?.run?.current_date
          if (currentDate) {
            await loadHoldingCloses(Object.keys(positions.value), currentDate)
          }
          reasoning.value = result.reasoning || ''
          await loadRunList()
          if (result.run?.start_date && result.run.start_date !== form.value.startDate) {
            toast.success(`回测创建成功，开始日已自动调整为 ${result.run.start_date}`)
          } else {
            toast.success('回测创建成功')
          }
          loading.value = false
        },
        onFailed: (err) => {
          toast.error('创建失败: ' + err)
          loading.value = false
        },
        onPollError: (err) => {
          toast.warning('任务仍在后台运行，请勿重复创建（' + err + '）')
        }
      }
    )
  } catch (e) {
    toast.error('创建失败: ' + (e.message || '未知错误'))
    loading.value = false
  }
}

async function onStep () {
  if (!run.value) return
  stepLoading.value = true
  try {
    const { task_id: taskId } = await backtestApi.stepAsync(run.value.id)
    toast.info('已开始执行下一天，AI 思考中...')
    resumeStepTask(taskId)
  } catch (e) {
    toast.error('步进失败: ' + (e.message || '未知错误'))
    stepLoading.value = false
  }
}

async function onAuto () {
  if (!run.value) return
  if (!form.value.endDate) {
    toast.warning('自动运行需要设置结束日期')
    return
  }
  autoRunning.value = true
  try {
    const { task_id: taskId } = await backtestApi.auto(run.value.id, form.value.endDate)
    startPoll(taskId)
  } catch (e) {
    autoRunning.value = false
    toast.error('自动运行失败: ' + (e.message || '未知错误'))
  }
}

async function onRevert () {
  if (!run.value) return
  try {
    const data = await backtestApi.revert(run.value.id)
    run.value = data
    await loadRun(run.value.id)
    renderCharts()
    toast.success(`已撤回一天，当前日期为 ${run.value.current_date}`)
  } catch (e) {
    toast.error('撤回失败: ' + (e.message || '未知错误'))
  }
}

async function onRunChange () {
  const id = Number(selectedRunId.value)
  if (id && id !== run.value?.id) {
    await loadRun(id)
  }
}

function onDelete () {
  if (!run.value) return
  showDeleteConfirm.value = true
}

async function doDelete () {
  if (!run.value) return
  try {
    const deletedId = run.value.id
    await backtestApi.delete(deletedId)
    clearInterval(pollTimer)
    runList.value = runList.value.filter(r => r.id !== deletedId)
    if (runList.value.length) {
      selectedRunId.value = runList.value[0].id
      await loadRun(selectedRunId.value)
    } else {
      selectedRunId.value = null
      run.value = null
      snapshots.value = []
      trades.value = []
      decisions.value = []
      pool.value = []
      closeMap.value = {}
      reasoning.value = ''
    }
    toast.success('回测已删除')
  } catch (e) {
    toast.error('删除失败: ' + (e.message || '未知错误'))
  } finally {
    showDeleteConfirm.value = false
  }
}

function onClearAll () {
  showClearAllConfirm.value = true
}

async function doClearAll () {
  try {
    await backtestApi.batchDelete()
    clearInterval(pollTimer)
    runList.value = []
    selectedRunId.value = null
    run.value = null
    snapshots.value = []
    trades.value = []
    decisions.value = []
    pool.value = []
    closeMap.value = {}
    reasoning.value = ''
    toast.success('历史回测已清空')
  } catch (e) {
    toast.error('清空失败: ' + (e.message || '未知错误'))
  } finally {
    showClearAllConfirm.value = false
  }
}

function renderCharts () {
  nextTick(() => {
    renderTrendChart()
    renderDailyPnlChart()
  })
}

function renderTrendChart () {
  if (!snapshots.value.length) return
  const dates = snapshots.value.map(i => i.trade_date)
  const assets = snapshots.value.map(i => Number(i.total_asset).toFixed(2))
  trendRef.init({
    tooltip: {
      trigger: 'axis',
      formatter: p => `${p[0].name}<br/>总资产: ${Number(p[0].value).toFixed(2)}`
    },
    grid: { left: 50, right: 20, top: 20, bottom: 25 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'var(--rule)' } },
      axisLabel: { color: 'var(--text-muted)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { show: false },
      axisLabel: { color: 'var(--text-muted)', fontSize: 10 }
    },
    series: [{
      type: 'line',
      data: assets,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#3b82f6', width: 2 },
      itemStyle: { color: '#3b82f6', borderWidth: 2, borderColor: '#fff' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.25)' }, { offset: 1, color: 'rgba(59,130,246,0.02)' }] } }
    }]
  })
}

function renderDailyPnlChart () {
  if (!snapshots.value.length) return
  const dates = snapshots.value.map(i => i.trade_date)
  const pnls = snapshots.value.map(i => Number(i.daily_pnl))
  const upColor = getThemeColor('--up')
  const downColor = getThemeColor('--down')
  dailyPnlRef.init({
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/>当日盈亏: ${Number(p[0].value).toFixed(2)}` },
    grid: { left: 50, right: 20, top: 20, bottom: 25 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'var(--rule)' } },
      axisLabel: { color: 'var(--text-muted)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'var(--rule)' } },
      axisLabel: { color: 'var(--text-muted)', fontSize: 10 }
    },
    series: [{
      type: 'bar',
      data: pnls.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? upColor : downColor }
      })),
      barWidth: '60%'
    }]
  })
}

watch(snapshots, renderCharts, { deep: true })

onMounted(async () => {
  // 默认开始日期为当年 5 月 1 日，结束日期为今天
  const today = new Date()
  form.value.endDate = today.toISOString().slice(0, 10)
  form.value.startDate = `${today.getFullYear()}-05-01`
  // 先加载历史回测列表，再自动选中最近一条进行中的回测
  await loadRunList()
  await loadLatestRun()
})

async function loadRunList () {
  try {
    const data = await backtestApi.getList({ page_size: 100 })
    runList.value = (data?.list || []).sort(
      (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
    )
  } catch (e) {
    runList.value = []
  }
}

async function loadLatestRun () {
  try {
    const data = await backtestApi.getList({ status: 'running', page_size: 1 })
    const latest = data?.list?.[0]
    if (latest?.id) {
      selectedRunId.value = latest.id
      await loadRun(latest.id)
    }
  } catch (e) {
    // 静默失败，保持空状态
  }
}
</script>

<template>
  <div class="backtest page">
    <PageHero
      section="资产"
      number="06"
      title="回测"
      description="选择起始日期，让 AI 在每个交易日基于历史 K 线决定买卖，支持手动步进与自动运行。"
      meta="AI 回测"
    >
      <template #actions>
        <div class="form-row inline">
          <label>开始日<input v-model="form.startDate" type="date"></label>
          <label>结束日<input v-model="form.endDate" type="date"></label>
          <label>初始资金<input v-model.number="form.initialCapital" type="number" step="100"></label>
          <label>AI 模型
            <select v-model="form.aiModel" class="model-select">
              <option value="kimi-k2.7">Kimi k2.7</option>
              <option value="deepseek-v4-pro">DeepSeek V4 Pro</option>
            </select>
          </label>
          <button class="btn-config" @click="onCreate" :disabled="loading">创建回测</button>
        </div>
      </template>
    </PageHero>

    <div v-if="run" class="run-panel">
      <BacktestStatsCards :run="run" :snapshot="latestSnapshot" />

      <div class="control-bar">
        <div class="run-info">
          <select v-model="selectedRunId" class="run-select" @change="onRunChange">
            <option v-for="r in runList" :key="r.id" :value="r.id">
              #{{ r.id }} · {{ r.start_date }} ~ {{ r.end_date || '进行中' }} · {{ r.status }}
            </option>
          </select>
          <span v-if="run" class="status" :class="run.status">{{ run.status }}</span>
        </div>
        <div class="actions">
          <button
            class="btn-danger"
            :disabled="autoRunning || stepLoading"
            @click="onDelete"
          >
            删除回测
          </button>
          <button
            class="btn-danger"
            :disabled="autoRunning || stepLoading || !runList.length"
            @click="onClearAll"
          >
            清空全部
          </button>
          <button
            class="btn-config"
            :disabled="stepLoading || autoRunning || run.status !== 'running' || run.current_date <= run.start_date"
            @click="onRevert"
          >
            撤回一天
          </button>
          <button
            class="btn-primary"
            :disabled="stepLoading || autoRunning || run.status !== 'running'"
            @click="onStep"
          >
            {{ stepLoading ? 'AI 思考中…' : '下一天' }}
          </button>
          <button
            class="btn-config"
            :disabled="autoRunning || run.status !== 'running'"
            @click="onAuto"
          >
            {{ autoRunning ? '自动运行中…' : '自动运行' }}
          </button>
        </div>
      </div>

      <div v-if="reasoning" class="reasoning-card">
        <div class="reasoning-title">AI 决策理由</div>
        <div class="reasoning-body">{{ reasoning }}</div>
      </div>

      <div class="charts-grid">
        <div class="chart-card">
          <div class="chart-title">资产趋势</div>
          <div :ref="trendRef.chartRef" class="chart-body" />
        </div>
        <div class="chart-card">
          <div class="chart-title">每日盈亏</div>
          <div :ref="dailyPnlRef.chartRef" class="chart-body" />
        </div>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'positions' }" @click="activeTab = 'positions'">当前持仓</button>
        <button class="tab" :class="{ active: activeTab === 'trades' }" @click="activeTab = 'trades'">交易记录</button>
        <button class="tab" :class="{ active: activeTab === 'pool' }" @click="activeTab = 'pool'">可买入池</button>
        <button class="tab" :class="{ active: activeTab === 'snapshots' }" @click="activeTab = 'snapshots'">每日快照</button>
        <button class="tab" :class="{ active: activeTab === 'decisions' }" @click="activeTab = 'decisions'">AI 日志</button>
      </div>

      <BacktestPositionTable
        v-if="activeTab === 'positions'"
        :positions="positions"
        :close-map="closeMap"
        :sort-field="positionSort.sortField"
        :sort-order="positionSort.sortOrder"
        @sort="positionSort.handleSort"
      />

      <BacktestTradeTable
        v-else-if="activeTab === 'trades'"
        :list="trades"
        :loading="loading"
        :sort-field="tradeSort.sortField"
        :sort-order="tradeSort.sortOrder"
        @sort="tradeSort.handleSort"
      />

      <BacktestPoolTable
        v-else-if="activeTab === 'pool'"
        :list="pool"
        :sort-field="poolSort.sortField"
        :sort-order="poolSort.sortOrder"
        @sort="poolSort.handleSort"
      />

      <div v-else-if="activeTab === 'snapshots'" class="table-wrap">
        <table class="stock-table">
          <thead>
            <tr>
              <th>日期</th>
              <th class="num">现金</th>
              <th class="num">总市值</th>
              <th class="num">总资产</th>
              <th class="num">当日盈亏</th>
              <th class="num">累计盈亏</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in snapshots" :key="s.trade_date" class="data-row">
              <td class="mono">{{ s.trade_date }}</td>
              <td class="num">{{ fmt(s.cash) }}</td>
              <td class="num">{{ fmt(s.total_market_value) }}</td>
              <td class="num">{{ fmt(s.total_asset) }}</td>
              <td class="num" :class="Number(s.daily_pnl) > 0 ? 'up' : Number(s.daily_pnl) < 0 ? 'down' : ''">{{ fmt(s.daily_pnl) }}</td>
              <td class="num" :class="Number(s.cumulative_pnl) > 0 ? 'up' : Number(s.cumulative_pnl) < 0 ? 'down' : ''">{{ fmt(s.cumulative_pnl) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="activeTab === 'decisions'" class="table-wrap">
        <table class="stock-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>解析动作</th>
              <th class="num">耗时(ms)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in decisions" :key="d.id" class="data-row">
              <td class="mono">{{ d.trade_date }}</td>
              <td class="mono"><pre>{{ d.parsed_actions }}</pre></td>
              <td class="num">{{ d.latency_ms ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        :visible="showDeleteConfirm"
        title="删除回测"
        :message="`确定删除回测 #${run?.id} 及其所有交易、快照、AI 决策数据？`"
        confirm-text="删除"
        cancel-text="取消"
        @confirm="doDelete"
        @cancel="showDeleteConfirm = false"
      />

      <ConfirmDialog
        :visible="showClearAllConfirm"
        title="清空全部回测"
        message="确定清空所有历史回测数据？此操作不可恢复。"
        confirm-text="清空"
        cancel-text="取消"
        @confirm="doClearAll"
        @cancel="showClearAllConfirm = false"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.backtest {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: auto;

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;

  &.inline {
    label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--text-secondary);
    }
  }

  input {
    padding: 6px 8px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 6px;
    font-size: 13px;
    outline: none;

    &:focus {
      border-color: var(--border-focus);
    }
  }

  .model-select {
    padding: 6px 8px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 6px;
    font-size: 13px;
    outline: none;
    cursor: pointer;

    &:focus {
      border-color: var(--border-focus);
    }

    option {
      background: var(--bg-secondary);
      color: var(--text-primary);
    }
  }
}

.btn-config {
  padding: 7px 14px;
  border: 1px solid var(--rule);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: var(--text-secondary);
  background: transparent;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--accent);
  }
}

.btn-danger {
  padding: 7px 14px;
  border: 1px solid var(--up);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: var(--up);
  background: transparent;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    background: var(--up);
    color: #fff;
  }
}

.btn-primary {
  padding: 7px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: #fff;
  background: var(--accent);

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    background: var(--accent-hover);
  }
}

.run-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 10px 14px;
}

.run-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: var(--text-muted);

  &.running {
    background: var(--accent);
  }

  &.completed {
    background: #10b981;
  }

  &.failed {
    background: var(--up);
  }
}

.actions {
  display: flex;
  gap: 8px;
}

.run-select {
  padding: 5px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  outline: none;

  &:focus {
    border-color: var(--border-focus);
  }

  option {
    background: var(--bg-secondary);
    color: var(--text-primary);
  }
}

.reasoning-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reasoning-title {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-faint);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.reasoning-body {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 200px;
}

.chart-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
}

.chart-body {
  flex: 1;
  min-height: 160px;
}

.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--rule);
  margin-top: 4px;
}

.tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: -1px;

  &:hover {
    color: var(--text-secondary);
  }

  &.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 500;
  }
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
}
</style>
