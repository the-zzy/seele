<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEChart } from '@/composables/useEChart'
import { boardApi } from '@/api/stock'
import BasePagination from '@/components/common/BasePagination.vue'

const route = useRoute()
const router = useRouter()
const code = route.params.code || ''

const { chartRef, init, resize } = useEChart()
const board = ref(null)
const allDaily = ref([])
const dailyLoading = ref(false)
const chartReady = ref(false)
const constituents = ref([])
const constLoading = ref(false)
const constPageNum = ref(1)
const constPageSize = ref(5)
const constTableRows = ref([])

const latestQuote = computed(() => {
  if (!board.value || board.value.latest_close == null) return null
  return {
    close: board.value.latest_close,
    pct_chg: board.value.latest_pct_chg
  }
})

function categoryLabel (category) {
  const map = { industry: '行业板块', concept: '概念板块', etf: 'ETF' }
  return map[category] || category
}

function getPriceClass (val) {
  if (val === null || val === undefined) return ''
  const v = parseFloat(val)
  if (v > 0) return 'up'
  if (v < 0) return 'down'
  return ''
}

function formatChg (val) {
  if (val === null || val === undefined) return '—'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function formatAmount (val) {
  if (val === null || val === undefined) return '—'
  if (val >= 100000000) return (val / 100000000).toFixed(2) + '亿'
  if (val >= 10000) return (val / 10000).toFixed(0) + '万'
  return val.toFixed(0)
}

function goBack () {
  router.push({ name: 'board-list' })
}

function goStock (symbol) {
  router.push({ name: 'stock-kline', params: { symbol } })
}

function updateConstTableRows () {
  const start = (constPageNum.value - 1) * constPageSize.value
  constTableRows.value = constituents.value.slice(start, start + constPageSize.value)
}

function handleConstPageChange (newPage) {
  constPageNum.value = newPage
  updateConstTableRows()
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

function initChart (list) {
  if (!chartRef.value) {
    console.warn('[BoardDetail] chartRef not ready')
    return
  }

  try {
    const dates = list.map(item => item.trade_date)
    const klineData = list.map(item => [item.open, item.close, item.low, item.high])
    const volumes = list.map(item => ({
      value: item.volume,
      itemStyle: {
        color: item.close >= item.open ? '#ef4444' : '#22c55e'
      }
    }))

    const total = dates.length
    const defaultCount = 100
    const startPercent = total > defaultCount ? ((total - defaultCount) / total) * 100 : 0

    const isDark = document.documentElement.dataset.theme !== 'light'
    const axisColor = isDark ? '#52525b' : '#adb5bd'
    const splitLineColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'
    const textColor = isDark ? '#a1a1aa' : '#495057'
    const tooltipBg = isDark ? 'rgba(17,17,17,0.95)' : 'rgba(255,255,255,0.98)'
    const tooltipBorder = isDark ? '#2a2a2a' : '#dee2e6'
    const tooltipText = isDark ? '#f5f5f5' : '#212529'

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: tooltipBg,
        borderColor: tooltipBorder,
        textStyle: { color: tooltipText, fontFamily: 'Consolas, Menlo, monospace', fontSize: 11 },
        formatter (params) {
          const kline = params.find(p => p.seriesName === '日K')
          if (!kline) return ''
          const item = list[kline.dataIndex]
          if (!item) return ''
          const chg = item.pct_chg?.toFixed(2) || '0.00'
          const chgColor = item.pct_chg >= 0 ? '#ef4444' : '#22c55e'
          let html = '<div style="font-family:Consolas,Menlo,monospace;font-size:11px;line-height:1.7;">'
          html += `<div style="font-weight:600;margin-bottom:6px;letter-spacing:0.06em;">${kline.axisValue}</div>`
          html += `<div>OPEN&nbsp;&nbsp;${item.open.toFixed(2)}</div>`
          html += `<div>CLOSE&nbsp;${item.close.toFixed(2)}</div>`
          html += `<div>HIGH&nbsp;&nbsp;${item.high.toFixed(2)}</div>`
          html += `<div>LOW&nbsp;&nbsp;&nbsp;${item.low.toFixed(2)}</div>`
          html += `<div>CHG&nbsp;&nbsp;&nbsp;<span style="color:${chgColor};font-weight:600">${chg}%</span></div>`
          params.forEach(p => {
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
        textStyle: { color: textColor, fontFamily: 'Consolas, Menlo, monospace', fontSize: 10 },
        icon: 'roundRect',
        itemWidth: 14,
        itemHeight: 3
      },
      grid: [
        { left: '8%', right: '4%', top: '6%', height: '60%' },
        { left: '8%', right: '4%', top: '74%', height: '14%' }
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
        { type: 'inside', xAxisIndex: [0, 1], start: startPercent, end: 100 },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: '92%',
          start: startPercent,
          end: 100,
          height: 18,
          borderColor: 'transparent',
          fillerColor: 'rgba(59,130,246,0.12)',
          handleStyle: { color: '#3b82f6' },
          textStyle: { color: textColor, fontFamily: 'Consolas, Menlo, monospace', fontSize: 9 },
          dataBackground: {
            lineStyle: { color: axisColor, opacity: 0.3 },
            areaStyle: { color: axisColor, opacity: 0.15 }
          },
          selectedDataBackground: {
            lineStyle: { color: '#3b82f6' },
            areaStyle: { color: 'rgba(59,130,246,0.2)' }
          }
        }
      ],
      series: [
        {
          name: '日K',
          type: 'candlestick',
          data: klineData,
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
          data: calculateMa(5, klineData),
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.2, color: '#f59e0b' }
        },
        {
          name: 'MA10',
          type: 'line',
          data: calculateMa(10, klineData),
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.2, color: '#3b82f6' }
        },
        {
          name: 'MA20',
          type: 'line',
          data: calculateMa(20, klineData),
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
    chartReady.value = true
  } catch (err) {
    console.error('[BoardDetail] chart init error:', err)
    chartReady.value = false
  }
}

async function loadBoard () {
  if (!code) return
  try {
    const res = await boardApi.getList({ page_num: 1, page_size: 1, keyword: code })
    board.value = res?.list?.[0] || null
  } catch (_) { /* ignore */ }
}

async function loadDaily () {
  if (!code) return
  dailyLoading.value = true
  try {
    const res = await boardApi.getDaily({ code, page_num: 1, page_size: 1000 })
    const list = res?.list || []
    allDaily.value = list.sort((a, b) => a.trade_date.localeCompare(b.trade_date))
    if (allDaily.value.length > 0) {
      initChart(allDaily.value)
    }
  } catch (err) {
    console.error('[BoardDetail] loadDaily error:', err)
    allDaily.value = []
  } finally {
    dailyLoading.value = false
  }
}

async function loadConstituents () {
  if (!code) return
  constLoading.value = true
  try {
    const res = await boardApi.getConstituents(code)
    constituents.value = Array.isArray(res) ? res : []
    constPageNum.value = 1
    updateConstTableRows()
  } catch (_) {
    constituents.value = []
  } finally {
    constLoading.value = false
  }
}

onMounted(() => {
  loadBoard()
  loadDaily()
  loadConstituents()
})
</script>

<template>
  <div class="board-kline-page page">
    <!-- 顶部导航栏（参考个股 K 线页样式） -->
    <div class="detail-bar">
      <button class="back-btn" @click="goBack">
        <span class="arrow">←</span>
        <span>返回</span>
      </button>
      <span class="bar-divider" />
      <div class="bar-meta">
        <span class="bar-section">板块 K 线</span>
        <h1 class="bar-name">{{ board?.name || '板块详情' }}</h1>
        <span class="bar-symbol">{{ code }}</span>
        <span v-if="board?.category" class="bar-category">{{ categoryLabel(board.category) }}</span>
        <span v-if="latestQuote" class="bar-price">
          <span class="price-num">{{ Number(latestQuote.close).toFixed(2) }}</span>
          <span
            class="price-chg"
            :class="latestQuote.pct_chg >= 0 ? 'up' : 'down'"
          >{{ latestQuote.pct_chg >= 0 ? '+' : '' }}{{ Number(latestQuote.pct_chg).toFixed(2) }}%</span>
        </span>
      </div>
    </div>

    <!-- 最新行情卡片 -->
    <div v-if="board?.latest_close != null" class="latest-card">
      <div class="latest-row">
        <div class="latest-item">
          <span class="latest-label">收盘</span>
          <span class="latest-value" :class="getPriceClass(board.latest_pct_chg)">
            {{ board.latest_close?.toFixed(2) }}
          </span>
        </div>
        <div class="latest-item">
          <span class="latest-label">涨跌幅</span>
          <span class="latest-value" :class="getPriceClass(board.latest_pct_chg)">
            {{ formatChg(board.latest_pct_chg) }}
          </span>
        </div>
        <div class="latest-item">
          <span class="latest-label">日期</span>
          <span class="latest-value plain">{{ board.latest_trade_date || '—' }}</span>
        </div>
        <div class="latest-item">
          <span class="latest-label">成交额</span>
          <span class="latest-value plain">{{ formatAmount(board.amount) }}</span>
        </div>
        <div class="latest-item">
          <span class="latest-label">5日涨幅</span>
          <span class="latest-value" :class="getPriceClass(board.chg_5d)">{{ formatChg(board.chg_5d) }}</span>
        </div>
        <div class="latest-item">
          <span class="latest-label">10日涨幅</span>
          <span class="latest-value" :class="getPriceClass(board.chg_10d)">{{ formatChg(board.chg_10d) }}</span>
        </div>
      </div>
    </div>

    <!-- K 线图 -->
    <div class="chart-section">
      <div class="section-title">日 K 线</div>
      <div class="chart-frame">
        <div ref="chartRef" class="kline-chart"></div>
        <div v-if="dailyLoading" class="chart-overlay">加载中…</div>
        <div v-else-if="allDaily.length === 0" class="chart-overlay">暂无数据</div>
        <div v-else-if="!chartReady" class="chart-overlay" style="color: var(--danger)">图表渲染失败，请检查控制台</div>
      </div>
    </div>

    <!-- 成分股 -->
    <div class="section-block">
      <div class="section-title">成分股（{{ constituents.length }}）</div>
      <div class="table-section">
        <div v-if="constLoading" class="state loading">加载中…</div>
        <div v-else-if="constituents.length === 0" class="state empty">暂无成分股数据</div>
        <table v-else class="stock-table">
          <colgroup>
            <col style="width:10%" />
            <col style="width:12%" />
            <col style="width:10%" />
            <col style="width:9%" />
            <col style="width:9%" />
            <col style="width:9%" />
            <col style="width:9%" />
            <col style="width:9%" />
            <col style="width:10%" />
            <col style="width:13%" />
          </colgroup>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>日期</th>
              <th>开盘</th>
              <th>最高</th>
              <th>最低</th>
              <th>收盘</th>
              <th>涨跌幅</th>
              <th>成交量</th>
              <th>成交额</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in constTableRows"
              :key="c.symbol"
              class="const-row"
              @dblclick="goStock(c.symbol)"
            >
              <td class="code">{{ c.symbol }}</td>
              <td class="name">{{ c.name || '—' }}</td>
              <td>{{ c.trade_date || '—' }}</td>
              <td>{{ c.open != null ? c.open.toFixed(2) : '—' }}</td>
              <td>{{ c.high != null ? c.high.toFixed(2) : '—' }}</td>
              <td>{{ c.low != null ? c.low.toFixed(2) : '—' }}</td>
              <td :class="getPriceClass(c.pct_chg)">{{ c.close != null ? c.close.toFixed(2) : '—' }}</td>
              <td :class="getPriceClass(c.pct_chg)">{{ formatChg(c.pct_chg) }}</td>
              <td>{{ c.volume != null ? (c.volume / 10000).toFixed(0) + '万' : '—' }}</td>
              <td>{{ formatAmount(c.amount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <BasePagination
        v-if="constituents.length > constPageSize"
        :page-num="constPageNum"
        :page-size="constPageSize"
        :total="constituents.length"
        @update:page-num="handleConstPageChange"
        @update:page-size="() => {}"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

.board-kline-page {
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

.bar-category {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  padding: 1px 8px;
  border: 1px solid var(--rule);
  border-radius: 3px;
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

.latest-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 14px 18px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.latest-row {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.latest-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 80px;
}

.latest-label {
  font-size: 11px;
  color: var(--text-faint);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.latest-value {
  font-size: 18px;
  font-weight: 600;
  font-family: var(--font-mono);
  &.plain { color: var(--text-primary); }
}

.up { color: #22c55e; }
.down { color: #ef4444; }

.section-block {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--rule);
  font-family: var(--font-display);
}

.chart-section {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.chart-frame {
  height: 420px;
  position: relative;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--bg-secondary);
  overflow: hidden;
}

.kline-chart {
  width: 100%;
  height: 100%;
}

.chart-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 13px;
  color: var(--text-faint);
}

.const-row {
  cursor: pointer;
  transition: background 0.12s;

  &:hover {
    background: var(--bg-tertiary);
  }

  .code {
    font-family: var(--font-mono);
    color: var(--accent);
  }

  .name {
    color: var(--text-primary);
  }
}
</style>
