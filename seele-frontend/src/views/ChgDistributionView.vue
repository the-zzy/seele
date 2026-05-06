<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEChart } from '@/composables/useEChart'
import { stockDailyApi } from '@/api/stock'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const { chartRef, instance, init } = useEChart()
const chartStartDate = ref('')
const chartEndDate = ref('')
const chartThreshold = ref(2.0)
const amountMa5Min = ref(20000)
const amountMa10Min = ref(20000)
const turnoverMa5Min = ref(2.0)
const turnoverMa10Min = ref(2.0)
const chartLoading = ref(false)

function getDefaultChartDates () {
  const today = new Date()
  const end = today.toISOString().split('T')[0]
  const start = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  return { start, end }
}

function buildOption (data) {
  const dates = data.map(item => item.trade_date)
  const percents = data.map(item => item.matched_percent)

  const isDark = document.documentElement.dataset.theme !== 'light'
  const axisColor = isDark ? '#52525b' : '#adb5bd'
  const textColor = isDark ? '#a1a1aa' : '#495057'
  const splitColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? 'rgba(17, 17, 17, 0.95)' : 'rgba(255,255,255,0.98)',
      borderColor: isDark ? '#2a2a2a' : '#dee2e6',
      textStyle: {
        color: isDark ? '#f5f5f5' : '#212529',
        fontSize: 13
      },
      formatter: (params) => {
        const p = params[0]
        const item = data[p.dataIndex]
        return `${p.name}<br/>总股票数: ${item.total_stocks} 只<br/>涨幅超过 ${chartThreshold.value}% 的股票: ${item.matched_count} 只<br/>占比: ${item.matched_percent.toFixed(2)}%`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '14%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        color: textColor,
        fontSize: 12
      },
      axisLine: { lineStyle: { color: axisColor } },
      axisTick: { lineStyle: { color: axisColor } }
    },
    yAxis: {
      type: 'value',
      name: 'Matched %',
      nameTextStyle: {
        color: textColor,
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}%',
        color: textColor,
        fontSize: 12
      },
      axisLine: { lineStyle: { color: axisColor } },
      splitLine: { lineStyle: { color: splitColor } }
    },
    series: [
      {
        name: '涨幅占比',
        type: 'bar',
        data: percents,
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [4, 4, 0, 0]
        },
        barWidth: '58%',
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
          fontSize: 12,
          color: textColor
        }
      }
    ]
  }
}

function initChart (data) {
  const chart = init(buildOption(data))
  if (!chart) return

  chart.on('dblclick', (params) => {
    if (params.componentType === 'series') {
      const item = data[params.dataIndex]
      if (item && item.trade_date) {
        router.push({
          name: 'chg-distribution-detail',
          query: { date: item.trade_date }
        })
      }
    }
  })
}

async function handleChartQuery () {
  if (!chartStartDate.value || !chartEndDate.value) {
    alert('请选择日期范围')
    return
  }
  if (chartStartDate.value > chartEndDate.value) {
    alert('开始日期不能晚于结束日期')
    return
  }

  chartLoading.value = true
  try {
    const data = await stockDailyApi.getPctChgDistribution(
      chartStartDate.value,
      chartEndDate.value,
      chartThreshold.value,
      amountMa5Min.value * 10000,
      amountMa10Min.value * 10000,
      turnoverMa5Min.value,
      turnoverMa10Min.value
    )
    const dataList = data?.list || []
    if (dataList.length > 0) {
      initChart(dataList)
    } else {
      instance.value?.dispose()
    }
  } catch (error) {
    console.error('加载涨幅分布数据失败:', error)
    instance.value?.dispose()
  } finally {
    chartLoading.value = false
  }
}

onMounted(() => {
  const { start, end } = getDefaultChartDates()
  chartStartDate.value = start
  chartEndDate.value = end
  handleChartQuery()
})
</script>

<template>
  <div class="chg-distribution picker-page">
    <PageHero
      section="选股策略"
      number="03.1"
      title="涨幅分布统计"
      description="按日期区间统计单日涨幅超过阈值的标的占比，识别市场强弱节奏。双击柱状图查看当日入选名单。"
      meta="占比分布"
    />

    <div class="filter-section chart-filters">
      <div class="filter-item">
        <label>开始日期</label>
        <input v-model="chartStartDate" type="date" />
      </div>
      <div class="filter-item">
        <label>结束日期</label>
        <input v-model="chartEndDate" type="date" />
      </div>
      <div class="filter-item">
        <label>涨幅阈值 (%)</label>
        <input v-model.number="chartThreshold" type="number" step="0.1" min="0" />
      </div>
      <div class="filter-item">
        <label>5日平均成交额 ≥ (万)</label>
        <input v-model.number="amountMa5Min" type="number" step="1000" min="0" />
      </div>
      <div class="filter-item">
        <label>10日平均成交额 ≥ (万)</label>
        <input v-model.number="amountMa10Min" type="number" step="1000" min="0" />
      </div>
      <div class="filter-item">
        <label>5日平均换手率 ≥ (%)</label>
        <input v-model.number="turnoverMa5Min" type="number" step="0.1" min="0" />
      </div>
      <div class="filter-item">
        <label>10日平均换手率 ≥ (%)</label>
        <input v-model.number="turnoverMa10Min" type="number" step="0.1" min="0" />
      </div>
      <div class="filter-item filter-actions">
        <button class="btn-primary" @click="handleChartQuery">查询分布</button>
      </div>
    </div>

    <div ref="chartRef" class="chart-container"></div>
    <div v-if="chartLoading" class="chart-loading">加载图表中…</div>

    <div class="chart-tip">
      <span class="tip-tag">Tip</span>
      <span>双击柱状图查看当日符合条件的股票列表</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

.chg-distribution {
  // picker-page 通用，但本页 result-bar 不需要
}

.chart-filters {
  flex-shrink: 0;

  .filter-actions {
    margin-left: auto;
  }
}

.chart-container {
  flex: 1;
  min-height: 0;
  margin-top: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    border-radius: 4px;
    box-shadow: var(--shadow-soft);
  }
}

.chart-loading {
  text-align: center;
  padding: 12px;
  font-family: var(--font-body);
  color: var(--text-faint);
  font-size: 13px;
}

.chart-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  padding: 10px 14px;
  border: 1px dashed var(--rule);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;

  .tip-tag {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent);
    padding: 2px 8px;
    border-radius: 2px;
    background: var(--accent-subtle);
  }
}
</style>
