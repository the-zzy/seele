<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useEChart } from '@/composables/useEChart'
import { portfolioApi } from '@/api/portfolio'
import PageHero from '@/components/common/PageHero.vue'
import PortfolioStatsCards from '@/components/portfolio/PortfolioStatsCards.vue'
import PortfolioTradeModal from '@/components/portfolio/PortfolioTradeModal.vue'
import PortfolioPositionTable from '@/components/portfolio/PortfolioPositionTable.vue'
import PortfolioTradeTable from '@/components/portfolio/PortfolioTradeTable.vue'
import BasePagination from '@/components/common/BasePagination.vue'

// 统计数据
const summary = ref({
  total_invested: 0,
  total_market_value: 0,
  total_pnl: 0,
  total_pnl_pct: 0,
  realized_pnl: 0,
  unrealized_pnl: 0,
  position_count: 0,
  initial_capital: 35000,
  total_return_pct: 0
})

// 列表数据
const positions = ref([])
const trades = ref([])
const closedList = ref([])
const loading = ref(false)

// 交易记录分页
const tradePageNum = ref(1)
const tradePageSize = ref(10)
const tradeTotal = ref(0)

// 已清仓分页
const closedPageNum = ref(1)
const closedPageSize = ref(10)
const closedTotal = ref(0)

// 标签页
const activeTab = ref('positions') // positions | trades | closed

// 弹窗
const modalVisible = ref(false)
const modalType = ref('BUY')

// 初始资金编辑
const capitalModalVisible = ref(false)
const capitalInput = ref('')

// 分组筛选
const activeGroup = ref('')
const groupOptions = [
  { label: '全部', value: '' },
  { label: '默认', value: 'default' },
  { label: '核心仓', value: 'core' },
  { label: '观察仓', value: 'watch' },
  { label: '试错仓', value: 'trial' }
]

// 预警
const alerts = ref([])
const alertsVisible = ref(true)

// 图表
const trendRef = useEChart()
const dailyPnlRef = useEChart()
const pieRef = useEChart()
const barRef = useEChart()

// 计算持仓 + 清仓的收益对比数据
const pnlComparisonData = computed(() => {
  const data = []
  positions.value.forEach(p => {
    data.push({
      name: p.name,
      symbol: p.symbol,
      value: p.unrealized_pnl || 0,
      type: '持仓'
    })
  })
  closedList.value.slice(0, 20).forEach(c => {
    data.push({
      name: c.name,
      symbol: c.symbol,
      value: c.realized_pnl || 0,
      type: '已清仓'
    })
  })
  return data.sort((a, b) => b.value - a.value)
})

async function loadSummary () {
  try {
    const res = await portfolioApi.getSummary()
    summary.value = res || {}
  } catch (e) {
    console.error('加载总览失败:', e)
  }
}

async function loadPositions () {
  try {
    const res = await portfolioApi.getPositions(activeGroup.value || undefined)
    positions.value = res || []
  } catch (e) {
    console.error('加载持仓失败:', e)
  }
}

async function loadAlerts () {
  try {
    const res = await portfolioApi.getAlerts()
    alerts.value = res || []
  } catch (e) {
    console.error('加载预警失败:', e)
  }
}

async function onUpdatePosition (symbol, data) {
  try {
    await portfolioApi.updatePosition(symbol, data)
    await loadPositions()
    await loadAlerts()
  } catch (e) {
    alert('更新失败: ' + (e.message || '未知错误'))
  }
}

async function loadTrades () {
  try {
    const res = await portfolioApi.getTrades({
      page_num: tradePageNum.value,
      page_size: tradePageSize.value
    })
    trades.value = res?.list || []
    tradeTotal.value = res?.total || 0
  } catch (e) {
    console.error('加载交易记录失败:', e)
  }
}

async function loadClosed () {
  try {
    const res = await portfolioApi.getClosed({
      page_num: closedPageNum.value,
      page_size: closedPageSize.value
    })
    closedList.value = res?.list || []
    closedTotal.value = res?.total || 0
  } catch (e) {
    console.error('加载清仓记录失败:', e)
  }
}

function pnlClass (v) {
  if (v == null) return ''
  const n = Number(v)
  if (n > 0) return 'up'
  if (n < 0) return 'down'
  return ''
}

function getThemeColor (name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#999'
}

async function loadDailyPnl () {
  try {
    const res = await portfolioApi.getDailyPnl()
    const list = res || []
    renderTrendChart(list, summary.value.initial_capital || 0)
    renderDailyPnlChart(list)
  } catch (e) {
    console.error('加载每日盈亏失败:', e)
  }
}

async function loadDistribution () {
  try {
    const res = await portfolioApi.getDistribution()
    renderPieChart(res || [])
  } catch (e) {
    console.error('加载分布失败:', e)
  }
}

function renderTrendChart (list, initialCapital) {
  if (!list.length) return
  const dates = list.map(i => i.date)
  const totalAssets = list.map(i => Number((initialCapital || 0) + i.cumulative_pnl).toFixed(2))

  trendRef.init({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } },
      formatter: p => {
        const d = p[0]
        return `${d.name}<br/>总资产: ${Number(d.value).toFixed(2)}`
      }
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
    series: [
      {
        type: 'line',
        data: totalAssets,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#3b82f6', width: 2 },
        itemStyle: { color: '#3b82f6', borderWidth: 2, borderColor: '#fff' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.25)' }, { offset: 1, color: 'rgba(59,130,246,0.02)' }] } }
      }
    ]
  })
}

function renderDailyPnlChart (list) {
  if (!list.length) return
  const dates = list.map(i => i.date)
  const dailyPnls = list.map(i => i.daily_pnl)
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
      data: dailyPnls.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? upColor : downColor }
      })),
      barWidth: '60%'
    }]
  })
}

function renderPieChart (list) {
  const initialCapital = summary.value.initial_capital || 0
  const totalPnl = summary.value.total_pnl || 0
  const totalMarketValue = summary.value.total_market_value || 0
  const totalAsset = initialCapital + totalPnl
  const cash = totalAsset - totalMarketValue
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']
  const cashColor = '#64748b'
  const data = list.map((i, idx) => ({
    name: i.name,
    value: i.ratio,
    itemStyle: {
      color: colors[idx % colors.length],
      borderRadius: 4,
      borderColor: 'var(--bg-secondary)',
      borderWidth: 2
    }
  }))
  if (cash > 0 && totalAsset > 0) {
    data.push({
      name: '空余资金',
      value: Number((cash / totalAsset * 100).toFixed(4)),
      itemStyle: {
        color: cashColor,
        borderRadius: 4,
        borderColor: 'var(--bg-secondary)',
        borderWidth: 2
      }
    })
  }
  if (!data.length) {
    pieRef.init({ series: [{ type: 'pie', data: [] }] })
    return
  }
  pieRef.init({
    tooltip: {
      trigger: 'item',
      formatter: p => `${p.name}<br/>占总资产: ${p.percent}%`
    },
    legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { color: 'var(--text-secondary)', fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      data,
      label: { show: false }
    }]
  })
}

function renderBarChart () {
  const data = pnlComparisonData.value.slice(0, 10)
  if (!data.length) {
    barRef.init({
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', show: false, data: [] },
      series: [{ type: 'bar', data: [] }]
    })
    return
  }
  const upColor = getThemeColor('--up')
  const downColor = getThemeColor('--down')
  barRef.init({
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}: ${Number(p[0].value).toFixed(2)}` },
    grid: { left: 80, right: 20, top: 10, bottom: 20 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'var(--rule)' } },
      axisLabel: { color: 'var(--text-muted)', fontSize: 10 }
    },
    yAxis: {
      type: 'category',
      data: data.map(i => i.name).reverse(),
      axisLine: { lineStyle: { color: 'var(--rule)' } },
      axisLabel: { color: 'var(--text-secondary)', fontSize: 11 }
    },
    series: [{
      type: 'bar',
      data: data.map(i => ({
        value: i.value,
        itemStyle: {
          color: i.value >= 0 ? upColor : downColor,
          borderRadius: [0, 3, 3, 0]
        }
      })).reverse(),
      barWidth: 14
    }]
  })
}

async function refreshAll () {
  loading.value = true
  await Promise.all([
    loadSummary(),
    loadPositions(),
    loadTrades(),
    loadClosed(),
    loadDailyPnl(),
    loadDistribution(),
    loadAlerts()
  ])
  nextTick(() => {
    renderBarChart()
  })
  loading.value = false
}

async function onSyncPositions () {
  try {
    await portfolioApi.syncPositions()
    await refreshAll()
  } catch (e) {
    alert('同步失败: ' + (e.message || '未知错误'))
  }
}

function onGroupChange (group) {
  activeGroup.value = group
  loadPositions()
}

function openModal (type) {
  modalType.value = type
  modalVisible.value = true
}

function openCapitalModal () {
  capitalInput.value = String(summary.value.initial_capital || 35000)
  capitalModalVisible.value = true
}

async function onUpdateCapital () {
  const val = Number(capitalInput.value)
  if (!val || val <= 0) {
    alert('请输入有效的初始资金')
    return
  }
  try {
    await portfolioApi.updateConfig({ initial_capital: val })
    capitalModalVisible.value = false
    await loadSummary()
  } catch (e) {
    alert('设置失败: ' + (e.message || '未知错误'))
  }
}

async function onSubmitTrade (data) {
  try {
    await portfolioApi.createTrade(data)
    modalVisible.value = false
    await refreshAll()
  } catch (e) {
    alert('录入失败: ' + (e.message || '未知错误'))
  }
}

async function onDeleteTrade (id) {
  try {
    await portfolioApi.deleteTrade(id)
    await refreshAll()
  } catch (e) {
    alert('删除失败: ' + (e.message || '未知错误'))
  }
}

function onTradePageChange (page) {
  tradePageNum.value = page
  loadTrades()
}

function onTradePageSizeChange (size) {
  tradePageSize.value = size
  tradePageNum.value = 1
  loadTrades()
}

function onClosedPageChange (page) {
  closedPageNum.value = page
  loadClosed()
}

function onClosedPageSizeChange (size) {
  closedPageSize.value = size
  closedPageNum.value = 1
  loadClosed()
}

watch(activeTab, (tab) => {
  if (tab === 'trades') loadTrades()
  if (tab === 'closed') loadClosed()
})

onMounted(() => {
  refreshAll()
})
</script>

<template>
  <div class="portfolio page">
    <PageHero
      section="资产"
      number="05"
      title="持仓管理"
      description="录入买入与卖出记录，自动计算每日盈亏与总收益，支持多维度图表分析。"
      meta="个人持仓"
    >
      <template #actions>
        <span class="capital-hint">初始资金 {{ (summary.initial_capital || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
        <button class="btn-config" @click="onSyncPositions">同步持仓</button>
        <button class="btn-config" @click="openCapitalModal">设置资金</button>
        <button class="btn-primary" @click="openModal('BUY')">+ 买入</button>
        <button class="btn-sell" @click="openModal('SELL')">- 卖出</button>
      </template>
    </PageHero>

    <PortfolioStatsCards :summary="summary" />

    <!-- 预警提示 -->
    <div v-if="alerts.length && alertsVisible" class="alert-banner">
      <div class="alert-header">
        <span class="alert-icon">⚠️</span>
        <span class="alert-title">持仓预警 {{ alerts.length }} 条</span>
        <button class="alert-close" @click="alertsVisible = false">&times;</button>
      </div>
      <div class="alert-list">
        <div
          v-for="alert in alerts"
          :key="alert.symbol + alert.alert_type"
          class="alert-item"
          :class="alert.alert_type"
        >
          <span class="alert-symbol">{{ alert.name }} ({{ alert.symbol }})</span>
          <span class="alert-type">{{ alert.alert_type === 'stop_loss' ? '止损' : '止盈' }}</span>
          <span class="alert-price">现价 {{ Number(alert.current_price).toFixed(2) }}</span>
          <span class="alert-target">目标 {{ Number(alert.target_price).toFixed(2) }}</span>
          <span class="alert-pnl" :class="pnlClass(alert.pnl_pct)">{{ alert.pnl_pct > 0 ? '+' : '' }}{{ alert.pnl_pct }}%</span>
        </div>
      </div>
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
      <div class="chart-card">
        <div class="chart-title">持仓占比</div>
        <div :ref="pieRef.chartRef" class="chart-body" />
      </div>
      <div class="chart-card">
        <div class="chart-title">个股收益</div>
        <div :ref="barRef.chartRef" class="chart-body" />
      </div>
    </div>

    <div class="tabs">
      <button
        class="tab"
        :class="{ active: activeTab === 'positions' }"
        @click="activeTab = 'positions'"
      >
        当前持仓
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'trades' }"
        @click="activeTab = 'trades'"
      >
        交易记录
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'closed' }"
        @click="activeTab = 'closed'"
      >
        已清仓
      </button>
    </div>

    <!-- 分组筛选 -->
    <div v-if="activeTab === 'positions'" class="group-filter">
      <button
        v-for="opt in groupOptions"
        :key="opt.value"
        class="group-btn"
        :class="{ active: activeGroup === opt.value }"
        @click="onGroupChange(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <PortfolioPositionTable
      v-if="activeTab === 'positions'"
      :list="positions"
      :loading="loading"
      @update-position="onUpdatePosition"
    />

    <template v-if="activeTab === 'trades'">
      <PortfolioTradeTable
        :list="trades"
        :loading="loading"
        @delete="onDeleteTrade"
      />
      <BasePagination
        v-if="tradeTotal > 0"
        v-model:page-num="tradePageNum"
        v-model:page-size="tradePageSize"
        :total="tradeTotal"
        @update:page-num="onTradePageChange"
        @update:page-size="onTradePageSizeChange"
      />
    </template>

    <template v-if="activeTab === 'closed'">
      <div class="table-section">
        <div class="section-title">
          已清仓记录
          <span v-if="closedTotal" class="section-count">{{ closedTotal }} 笔</span>
        </div>
        <div class="table-wrap">
          <table class="stock-table">
            <thead>
              <tr>
                <th>股票代码</th>
                <th>股票名称</th>
                <th class="num">总买入</th>
                <th class="num">总卖出</th>
                <th class="num">手续费</th>
                <th class="num">实现盈亏</th>
                <th class="num">盈亏比例</th>
                <th class="num">持仓天数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="8" class="empty">加载中...</td>
              </tr>
              <tr v-else-if="!closedList.length">
                <td colspan="8" class="empty">暂无记录</td>
              </tr>
              <tr v-for="item in closedList" :key="item.id">
                <td class="mono">{{ item.symbol }}</td>
                <td>{{ item.name }}</td>
                <td class="num">{{ Number(item.total_buy_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</td>
                <td class="num">{{ Number(item.total_sell_amount).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</td>
                <td class="num">{{ Number(item.total_fee || 0).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</td>
                <td class="num" :class="Number(item.realized_pnl) > 0 ? 'up' : Number(item.realized_pnl) < 0 ? 'down' : ''">
                  {{ Number(item.realized_pnl).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
                </td>
                <td class="num" :class="Number(item.pnl_pct) > 0 ? 'up' : Number(item.pnl_pct) < 0 ? 'down' : ''">
                  {{ Number(item.pnl_pct).toFixed(2) }}%
                </td>
                <td class="num">
                  {{ Math.ceil((new Date(item.close_date) - new Date(item.open_date)) / (1000 * 60 * 60 * 24)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <BasePagination
        v-if="closedTotal > 0"
        v-model:page-num="closedPageNum"
        v-model:page-size="closedPageSize"
        :total="closedTotal"
        @update:page-num="onClosedPageChange"
        @update:page-size="onClosedPageSizeChange"
      />
    </template>

    <PortfolioTradeModal
      v-model:visible="modalVisible"
      :type="modalType"
      :positions="positions"
      @submit="onSubmitTrade"
    />

    <!-- 初始资金设置弹窗 -->
    <div v-if="capitalModalVisible" class="modal-overlay" @click.self="capitalModalVisible = false">
      <div class="modal-panel capital-panel">
        <div class="modal-header">
          <h3 class="modal-title">设置初始资金</h3>
          <button class="modal-close" @click="capitalModalVisible = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label>初始资金（元）</label>
            <input v-model="capitalInput" placeholder="如 35000" type="number" step="1">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-link" @click="capitalModalVisible = false">取消</button>
          <button class="btn-primary" @click="onUpdateCapital">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.portfolio {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: auto;
}

.alert-banner {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--rule);
}

.alert-icon {
  font-size: 14px;
}

.alert-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.alert-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;

  &:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--rule);
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  font-size: 12px;

  &.stop_loss {
    background: rgba(239, 68, 68, 0.04);
  }

  &.take_profit {
    background: rgba(16, 185, 129, 0.04);
  }
}

.alert-symbol {
  font-family: var(--font-mono);
  color: var(--text-primary);
  min-width: 120px;
}

.alert-type {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: var(--text-muted);

  .stop_loss & {
    background: var(--up);
  }

  .take_profit & {
    background: var(--down);
  }
}

.alert-price, .alert-target {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.alert-pnl {
  margin-left: auto;
  font-family: var(--font-mono);
  font-weight: 600;

  &.up {
    color: var(--up);
  }

  &.down {
    color: var(--down);
  }
}

.group-filter {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  margin-bottom: 4px;
}

.group-btn {
  padding: 5px 12px;
  border: 1px solid var(--rule);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-muted);
  background: transparent;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  &.active {
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(59, 130, 246, 0.08);
  }
}

.capital-hint {
  font-size: 13px;
  color: var(--text-faint);
  margin-right: 8px;
  font-family: var(--font-mono);
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

  &:hover {
    border-color: var(--accent);
    color: var(--accent);
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

  &:hover {
    background: var(--accent-hover);
  }
}

.btn-sell {
  padding: 7px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: #fff;
  background: var(--up);

  &:hover {
    background: #e04345;
  }
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.chart-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 260px;
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
  min-height: 220px;
}

.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--rule);
  margin-top: 8px;
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

.table-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 10px;
  width: 420px;
  max-width: 90vw;
  box-shadow: var(--shadow-soft);
}

.capital-panel {
  width: 360px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--rule);
}

.modal-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;

  &:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }
}

.modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  input {
    padding: 8px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 6px;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;

    &:focus {
      border-color: var(--border-focus);
    }
  }
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--rule);
}

.btn-link {
  padding: 7px 14px;
  background: transparent;
  color: var(--text-muted);
  border: none;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
}

</style>
