<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEChart } from '@/composables/useEChart'
import { financialApi } from '@/api/financial'

const route = useRoute()
const router = useRouter()

const symbol = ref(route.params.symbol || '')
const stockName = ref(route.query.name || '')

const loading = ref(false)
const dataReady = ref(false)
const financialData = ref(null)

const { chartRef: radarRef, init: initRadar } = useEChart()
const { chartRef: barRef, init: initBar } = useEChart()

function goBack () {
  router.back()
}

function formatNumber (val) {
  if (val == null || val === undefined) return '—'
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function formatPercent (val) {
  if (val == null || val === undefined) return '—'
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

async function loadData () {
  if (!symbol.value) return
  loading.value = true
  try {
    const res = await financialApi.getBySymbol(symbol.value)
    financialData.value = res
    dataReady.value = true
    await nextTick()
    initCharts()
  } catch (error) {
    console.error('加载财务数据失败:', error)
    dataReady.value = false
  } finally {
    loading.value = false
  }
}

function initCharts () {
  const d = financialData.value
  if (!d) return

  const isDark = document.documentElement.dataset.theme !== 'light'
  const textColor = isDark ? '#a1a1aa' : '#495057'
  const axisColor = isDark ? '#52525b' : '#adb5bd'
  const splitLineColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'

  // 雷达图
  const radarOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: isDark ? 'rgba(17,17,17,0.95)' : 'rgba(255,255,255,0.98)',
      borderColor: isDark ? '#2a2a2a' : '#dee2e6',
      textStyle: { color: isDark ? '#f5f5f5' : '#212529', fontSize: 11 }
    },
    radar: {
      indicator: [
        { name: 'ROE', max: 30 },
        { name: '毛利率', max: 80 },
        { name: '净利率', max: 50 },
        { name: '营收同比', max: 100 },
        { name: '净利润同比', max: 100 },
        { name: 'EPS', max: 10 }
      ],
      radius: '65%',
      axisName: { color: textColor, fontSize: 10 },
      splitLine: { lineStyle: { color: splitLineColor } },
      splitArea: { areaStyle: { color: ['transparent'] } },
      axisLine: { lineStyle: { color: axisColor } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          Math.max(0, d.roe || 0),
          Math.max(0, d.gross_profit_ratio || 0),
          Math.max(0, d.net_profit_ratio || 0),
          Math.max(0, d.revenue_yoy || 0),
          Math.max(0, d.net_profit_yoy || 0),
          Math.max(0, d.eps || 0)
        ],
        name: d.name || d.symbol,
        areaStyle: { color: 'rgba(59,130,246,0.2)' },
        lineStyle: { color: '#3b82f6', width: 2 },
        itemStyle: { color: '#3b82f6' }
      }]
    }]
  }

  // 柱状图：营收 vs 净利润
  const barOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? 'rgba(17,17,17,0.95)' : 'rgba(255,255,255,0.98)',
      borderColor: isDark ? '#2a2a2a' : '#dee2e6',
      textStyle: { color: isDark ? '#f5f5f5' : '#212529', fontSize: 11 },
      formatter (params) {
        let html = `<div style="font-weight:600;margin-bottom:4px">${d.name || d.symbol}</div>`
        params.forEach(p => {
          html += `<div>${p.marker} ${p.seriesName}: ${formatNumber(p.value)} 万元</div>`
        })
        return html
      }
    },
    grid: { left: '12%', right: '8%', top: '12%', bottom: '18%' },
    xAxis: {
      type: 'category',
      data: ['营业总收入', '净利润', '扣非净利润'],
      axisLine: { lineStyle: { color: axisColor } },
      axisLabel: { color: textColor, fontSize: 10 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: textColor, fontSize: 10 },
      splitLine: { lineStyle: { color: splitLineColor } }
    },
    series: [
      {
        name: '金额',
        type: 'bar',
        barWidth: '40%',
        data: [
          d.total_revenue || 0,
          d.net_profit || 0,
          d.deduct_net_profit || 0
        ],
        itemStyle: {
          color (p) {
            const colors = ['#3b82f6', '#22c55e', '#f59e0b']
            return colors[p.dataIndex] || '#3b82f6'
          },
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }

  initRadar(radarOption)
  initBar(barOption)
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="financial-page page">
    <div class="detail-bar">
      <button class="back-btn" @click="goBack">
        <span class="arrow">←</span>
        <span>返回</span>
      </button>
      <span class="bar-divider" />
      <div class="bar-meta">
        <span class="bar-section">财务分析</span>
        <h1 class="bar-name">{{ stockName || '—' }}</h1>
        <span class="bar-symbol">{{ symbol }}</span>
      </div>
    </div>

    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="!dataReady" class="state empty">暂无财务数据</div>
    <template v-else>
      <div class="fin-cards">
        <div class="fin-card">
          <span class="fin-label">净利润</span>
          <span class="fin-value">{{ formatNumber(financialData.net_profit) }}</span>
          <span class="fin-badge" :class="financialData.net_profit_yoy >= 0 ? 'up' : 'down'">
            {{ formatPercent(financialData.net_profit_yoy) }}
          </span>
        </div>
        <div class="fin-card">
          <span class="fin-label">营业收入</span>
          <span class="fin-value">{{ formatNumber(financialData.total_revenue) }}</span>
          <span class="fin-badge" :class="financialData.revenue_yoy >= 0 ? 'up' : 'down'">
            {{ formatPercent(financialData.revenue_yoy) }}
          </span>
        </div>
        <div class="fin-card">
          <span class="fin-label">ROE</span>
          <span class="fin-value">{{ formatPercent(financialData.roe) }}</span>
        </div>
        <div class="fin-card">
          <span class="fin-label">EPS</span>
          <span class="fin-value">{{ financialData.eps?.toFixed(2) || '—' }}</span>
        </div>
        <div class="fin-card">
          <span class="fin-label">毛利率</span>
          <span class="fin-value">{{ formatPercent(financialData.gross_profit_ratio) }}</span>
        </div>
        <div class="fin-card">
          <span class="fin-label">净利率</span>
          <span class="fin-value">{{ formatPercent(financialData.net_profit_ratio) }}</span>
        </div>
        <div class="fin-card">
          <span class="fin-label">资产负债率</span>
          <span class="fin-value">{{ formatPercent(financialData.debt_ratio) }}</span>
        </div>
        <div class="fin-card">
          <span class="fin-label">每股净资产</span>
          <span class="fin-value">{{ financialData.bps?.toFixed(2) || '—' }}</span>
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-title">财务能力雷达图</div>
          <div ref="radarRef" class="chart-box"></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">营收与利润</div>
          <div ref="barRef" class="chart-box"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.financial-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow-y: auto;
}

.detail-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 0 14px;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 12px;
  flex-shrink: 0;
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
  height: 22px;
  background: var(--rule);
}

.bar-meta {
  display: flex;
  align-items: baseline;
  gap: 14px;
  flex-wrap: wrap;
}

.bar-section {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.bar-name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0;
  line-height: 1.2;
}

.bar-symbol {
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
}

.state {
  text-align: center;
  padding: 60px 20px;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-faint);
}

.fin-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.fin-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 12px 16px;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 8px;
    bottom: 8px;
    width: 2px;
    background: var(--accent);
    border-radius: 0 1px 1px 0;
    opacity: 0.6;
  }
}

.fin-label {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-faint);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.fin-value {
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.fin-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  width: fit-content;
  padding: 1px 6px;
  border-radius: 2px;
  letter-spacing: 0.02em;

  &.up {
    color: var(--up);
    background: rgba(239, 68, 68, 0.12);
  }

  &.down {
    color: var(--down);
    background: rgba(34, 197, 94, 0.12);
  }
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex: 1;
  min-height: 320px;
}

.chart-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    border-radius: 4px;
    box-shadow: var(--shadow-soft);
    z-index: 1;
  }
}

.chart-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-bottom: 8px;
  flex-shrink: 0;
}

.chart-box {
  flex: 1;
  min-height: 0;
  position: relative;
  z-index: 0;
}

@media (max-width: 960px) {
  .fin-cards { grid-template-columns: repeat(2, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}
</style>
