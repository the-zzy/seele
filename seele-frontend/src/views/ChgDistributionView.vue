<script setup>
import { ref, onMounted } from 'vue'
import { useEChart } from '@/composables/useEChart'
import { toast } from '@/composables/useToast'
import { stockDailyApi } from '@/api/stock'
import PageHero from '@/components/common/PageHero.vue'

const { chartRef, instance, init } = useEChart()
const chartStartDate = ref('')
const chartEndDate = ref('')
const chartThreshold = ref(2.0)
const chartLoading = ref(false)

function getDefaultChartDates () {
  const today = new Date()
  const end = today.toISOString().split('T')[0]
  const start = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  return { start, end }
}

function buildOption (data) {
  const dates = data.map(item => item.trade_date)
  const percents = data.map(item => item.strong_percent)

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
        return `${p.name}<br/>总股票数: ${item.total_stocks} 只<br/>上涨: ${item.up_count} / 下跌: ${item.down_count}<br/>强势家数: ${item.strong_count}<br/>占比: ${item.strong_percent}%`
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
      name: '强势占比',
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
  init(buildOption(data))
}

async function handleChartQuery () {
  if (!chartStartDate.value || !chartEndDate.value) {
    toast.warning('请选择日期范围')
    return
  }
  if (chartStartDate.value > chartEndDate.value) {
    toast.warning('开始日期不能晚于结束日期')
    return
  }

  chartLoading.value = true
  try {
    const data = await stockDailyApi.getPctChgDistribution(
      chartStartDate.value,
      chartEndDate.value,
      chartThreshold.value
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
      section="市场情绪"
      number="02.1"
      title="涨幅分布统计"
      description="按日期区间统计每日市场涨跌家数及强势标的占比，识别市场强弱节奏。点击柱状图查看当日板块分布。"
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
        <label>强势阈值 (%)</label>
        <input v-model.number="chartThreshold" type="number" step="0.1" min="0" />
      </div>
      <div class="filter-item filter-actions">
        <button class="btn-primary" @click="handleChartQuery">查询分布</button>
      </div>
    </div>

    <div ref="chartRef" class="chart-container"></div>
    <div v-if="chartLoading" class="chart-loading">加载图表中…</div>

  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

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
  height: 360px;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    border-radius: 4px;
    box-shadow: var(--shadow-soft);
  }

  @media (max-width: 768px) {
    height: 320px;
  }
}

.chart-loading {
  text-align: center;
  padding: 12px;
  font-family: var(--font-body);
  color: var(--text-faint);
  font-size: 13px;
}

@media (max-width: 768px) {
  .chart-filters {
    flex-wrap: wrap;

    .filter-item {
      flex: 1 1 45%;
      min-width: 140px;

      input {
        width: 100%;
        box-sizing: border-box;
        min-height: var(--touch-target);
      }
    }

    .filter-actions {
      margin-left: 0;
      width: 100%;

      button {
        width: 100%;
        min-height: var(--touch-target);
      }
    }
  }
}

</style>
