<script setup>
/* eslint-disable */
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEChart } from '@/composables/useEChart'
import { stockDailyApi } from '@/api/stock'
import { financialApi } from '@/api/financial'

const route = useRoute()
const router = useRouter()

const symbol = ref(route.params.symbol || '')
const stockName = ref(route.query.name || '')

const { chartRef, init, resize } = useEChart()
const loading = ref(false)
const dataReady = ref(false)
const latestQuote = ref(null)

const financialData = ref(null)
const financialLoading = ref(false)
const financialReady = ref(false)

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

function calculateMa (dayCount, data) {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < dayCount) {
      result.push('-')
      continue
    }
    let sum = 0
    for (let j = 0; j < dayCount; j++) {
      sum += data[i - j][1]
    }
    result.push((sum / dayCount).toFixed(2))
  }
  return result
}

async function loadFinancial () {
  if (!symbol.value) return
  financialLoading.value = true
  try {
    const res = await financialApi.getBySymbol(symbol.value)
    financialData.value = res
    financialReady.value = true
  } catch (error) {
    console.error('加载财务数据失败:', error)
    financialData.value = null
    financialReady.value = false
  } finally {
    financialLoading.value = false
  }
}

async function loadData () {
  if (!symbol.value) return
  loading.value = true
  try {
    const data = await stockDailyApi.getBySymbol(symbol.value)
    if (Array.isArray(data) && data.length > 0) {
      const list = data.sort((a, b) => a.trade_date.localeCompare(b.trade_date))
      latestQuote.value = list[list.length - 1]
      const dates = list.map(item => item.trade_date)
      const klineData = list.map(item => [
        item.open,
        item.close,
        item.low,
        item.high
      ])
      const volumes = list.map((item) => ({
        value: item.volume,
        itemStyle: {
          color: item.close >= item.open ? '#ef4444' : '#22c55e'
        }
      }))

      const indicatorMap = new Map()
      list.forEach(item => {
        indicatorMap.set(item.trade_date, {
          ma5: item.ma5,
          ma10: item.ma10,
          ma20: item.ma20,
          ma30: item.ma30,
          ma60: item.ma60
        })
      })

      initChart(dates, klineData, volumes, list, indicatorMap)
      dataReady.value = true
    }
  } catch (error) {
    console.error('加载K线数据失败:', error)
  } finally {
    loading.value = false
  }
  loadFinancial()
}

function initChart (dates, data, volumes, list, indicatorMap) {
  if (!chartRef.value) return

  const total = dates.length
  const defaultCount = 100
  const startPercent = total > defaultCount
    ? ((total - defaultCount) / total) * 100
    : 0

  const isDark = document.documentElement.dataset.theme !== 'light'
  const axisColor = isDark ? '#52525b' : '#adb5bd'
  const splitLineColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'
  const textColor = isDark ? '#a1a1aa' : '#495057'
  const tooltipBg = isDark ? 'rgba(17, 17, 17, 0.95)' : 'rgba(255,255,255,0.98)'
  const tooltipBorder = isDark ? '#2a2a2a' : '#dee2e6'
  const tooltipText = isDark ? '#f5f5f5' : '#212529'

  function getMaSeries (period) {
    const key = 'ma' + period
    const fallback = calculateMa(period, data)
    return list.map((item, idx) => {
      const indicators = indicatorMap.get(item.trade_date)
      if (indicators && indicators[key] != null) {
        return Number(indicators[key]).toFixed(2)
      }
      return fallback[idx]
    })
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: {
        color: tooltipText,
        fontFamily: 'Consolas, Menlo, monospace',
        fontSize: 11
      },
      formatter (params) {
        const kline = params.find((p) => p.seriesName === '日K')
        if (!kline) return ''

        const idx = kline.dataIndex
        const item = list[idx]
        if (!item) return ''

        const open = item.open
        const close = item.close
        const low = item.low
        const high = item.high
        const change = item.pct_chg?.toFixed(2) || '0.00'
        const changeColor = item.pct_chg >= 0 ? '#ef4444' : '#22c55e'

        let html = '<div style="font-family:Consolas,Menlo,monospace;font-size:11px;line-height:1.7;">'
        html += `<div style="font-weight:600;margin-bottom:6px;letter-spacing:0.06em;">${kline.axisValue}</div>`
        html += `<div>OPEN&nbsp;&nbsp;${open.toFixed(2)}</div>`
        html += `<div>CLOSE&nbsp;${close.toFixed(2)}</div>`
        html += `<div>HIGH&nbsp;&nbsp;${high.toFixed(2)}</div>`
        html += `<div>LOW&nbsp;&nbsp;&nbsp;${low.toFixed(2)}</div>`
        html += `<div>CHG&nbsp;&nbsp;&nbsp;<span style="color:${changeColor};font-weight:600">${change}%</span></div>`

        params.forEach((p) => {
          if (p.seriesName === 'MA5') html += `<div>MA5&nbsp;&nbsp;&nbsp;${p.data}</div>`
          if (p.seriesName === 'MA10') html += `<div>MA10&nbsp;&nbsp;${p.data}</div>`
          if (p.seriesName === 'MA20') html += `<div>MA20&nbsp;&nbsp;${p.data}</div>`
        })

        html += '</div>'
        return html
      }
    },
    legend: {
      data: ['日K', 'MA5', 'MA10', 'MA20'],
      right: 16,
      top: 8,
      textStyle: {
        color: textColor,
        fontFamily: 'Consolas, Menlo, monospace',
        fontSize: 10
      },
      icon: 'roundRect',
      itemWidth: 14,
      itemHeight: 3
    },
    grid: [
      {
        left: '8%',
        right: '4%',
        top: '6%',
        height: '60%'
      },
      {
        left: '8%',
        right: '4%',
        top: '74%',
        height: '14%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false, lineStyle: { color: axisColor } },
        axisLabel: { color: textColor, fontFamily: 'Consolas, Menlo, monospace', fontSize: 10 },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: true,
        axisLine: { onZero: false, lineStyle: { color: axisColor } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        position: 'right',
        axisLine: { lineStyle: { color: axisColor } },
        axisLabel: { color: textColor, fontFamily: 'Consolas, Menlo, monospace', fontSize: 10 },
        splitLine: { lineStyle: { color: splitLineColor } }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        position: 'right',
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: startPercent,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        top: '92%',
        start: startPercent,
        end: 100,
        height: 18,
        borderColor: 'transparent',
        fillerColor: 'rgba(59, 130, 246, 0.12)',
        handleStyle: { color: '#3b82f6' },
        textStyle: {
          color: textColor,
          fontFamily: 'Consolas, Menlo, monospace',
          fontSize: 9
        },
        dataBackground: {
          lineStyle: { color: axisColor, opacity: 0.3 },
          areaStyle: { color: axisColor, opacity: 0.15 }
        },
        selectedDataBackground: {
          lineStyle: { color: '#3b82f6' },
          areaStyle: { color: 'rgba(59, 130, 246, 0.2)' }
        }
      }
    ],
    series: [
      {
        name: '日K',
        type: 'candlestick',
        data: data,
        itemStyle: {
          color: '#ef4444',
          color0: '#22c55e',
          borderColor: '#ef4444',
          borderColor0: '#22c55e'
        }
      },
      {
        name: 'MA5',
        type: 'line',
        data: getMaSeries(5),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#f59e0b' }
      },
      {
        name: 'MA10',
        type: 'line',
        data: getMaSeries(10),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#3b82f6' }
      },
      {
        name: 'MA20',
        type: 'line',
        data: getMaSeries(20),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#a855f7' }
      },
      {
        name: '成交量',
        type: 'bar',
        gridIndex: 1,
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes
      }
    ]
  }

  init(option)
  resize()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="kline-page page">
    <div class="detail-bar">
      <button class="back-btn" @click="goBack">
        <span class="arrow">←</span>
        <span>返回</span>
      </button>
      <span class="bar-divider" />
      <div class="bar-meta">
        <span class="bar-section">个股 K 线</span>
        <h1 class="bar-name">{{ stockName || '—' }}</h1>
        <span class="bar-symbol">{{ symbol }}</span>
        <span v-if="latestQuote" class="bar-price">
          <span class="price-num">{{ Number(latestQuote.close).toFixed(2) }}</span>
          <span
            class="price-chg"
            :class="latestQuote.pct_chg >= 0 ? 'up' : 'down'"
          >{{ latestQuote.pct_chg >= 0 ? '+' : '' }}{{ Number(latestQuote.pct_chg).toFixed(2) }}%</span>
        </span>
      </div>
    </div>

    <div class="chart-frame">
      <div ref="chartRef" class="kline-chart"></div>
      <div v-if="loading" class="kline-loading">载入图表…</div>
      <div v-else-if="!dataReady" class="kline-empty">暂无数据</div>
    </div>

    <div v-if="financialReady" class="financial-panel">
      <div class="fin-header">
        <span class="fin-title">财务指标</span>
        <span class="fin-meta">报告期 {{ financialData.report_date }}</span>
      </div>
      <div class="fin-grid">
        <div class="fin-item">
          <span class="fin-label">净利润</span>
          <span class="fin-value">{{ formatNumber(financialData.net_profit) }}</span>
          <span
            class="fin-badge"
            :class="financialData.net_profit_yoy >= 0 ? 'up' : 'down'"
          >{{ formatPercent(financialData.net_profit_yoy) }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">营业收入</span>
          <span class="fin-value">{{ formatNumber(financialData.total_revenue) }}</span>
          <span
            class="fin-badge"
            :class="financialData.revenue_yoy >= 0 ? 'up' : 'down'"
          >{{ formatPercent(financialData.revenue_yoy) }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">ROE</span>
          <span class="fin-value">{{ formatPercent(financialData.roe) }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">EPS</span>
          <span class="fin-value">{{ financialData.eps?.toFixed(2) || '—' }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">毛利率</span>
          <span class="fin-value">{{ formatPercent(financialData.gross_profit_ratio) }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">净利率</span>
          <span class="fin-value">{{ formatPercent(financialData.net_profit_ratio) }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">资产负债率</span>
          <span class="fin-value">{{ formatPercent(financialData.debt_ratio) }}</span>
        </div>
        <div class="fin-item">
          <span class="fin-label">每股净资产</span>
          <span class="fin-value">{{ financialData.bps?.toFixed(2) || '—' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.kline-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow-y: auto;

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
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

.bar-price {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  margin-left: 6px;
  font-variant-numeric: tabular-nums;

  .price-num {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .price-chg {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 2px;
    letter-spacing: 0.04em;

    &.up {
      color: var(--up);
      background: rgba(239, 68, 68, 0.12);
    }
    &.down {
      color: var(--down);
      background: rgba(34, 197, 94, 0.12);
    }
  }
}

.chart-frame {
  flex: 1;
  min-height: 0;
  position: relative;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--bg-secondary);
  overflow: hidden;

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

.kline-chart {
  width: 100%;
  height: 100%;
}

.kline-loading,
.kline-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-faint);
}

.financial-panel {
  flex-shrink: 0;
  margin-top: 12px;
  padding: 16px 20px;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--bg-secondary);
}

.fin-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}

.fin-title {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

.fin-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-faint);
  letter-spacing: 0.08em;
}

.fin-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.fin-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--bg-tertiary);
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
</style>
