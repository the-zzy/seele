<script setup>
import { ref, onMounted } from 'vue'
import { marketSentimentApi, stockDailyApi } from '@/api/stock'
import PageHero from '@/components/common/PageHero.vue'

const industryList = ref([])
const industryDate = ref('')
const industryLoading = ref(false)
const tradeDates = ref([])

async function loadTradeDates () {
  try {
    const dates = await stockDailyApi.getTradeDates()
    tradeDates.value = dates || []
    if (tradeDates.value.length > 0 && !industryDate.value) {
      industryDate.value = tradeDates.value[0]
      await loadIndustrySentiment(industryDate.value)
    }
  } catch (error) {
    console.error('加载交易日列表失败:', error)
  }
}

async function loadIndustrySentiment (tradeDate) {
  if (!tradeDate) return
  industryLoading.value = true
  try {
    const res = await marketSentimentApi.getIndustrySentiment(tradeDate)
    industryList.value = res?.list || []
  } catch (error) {
    console.error('加载板块情绪数据失败:', error)
    industryList.value = []
  } finally {
    industryLoading.value = false
  }
}

function handleQuery () {
  loadIndustrySentiment(industryDate.value)
}

function getIndustryClass (avgPctChg) {
  if (avgPctChg > 2) return 'strong-up'
  if (avgPctChg > 0) return 'up'
  if (avgPctChg < -2) return 'strong-down'
  if (avgPctChg < 0) return 'down'
  return 'flat'
}

onMounted(() => {
  loadTradeDates()
})
</script>

<template>
  <div class="industry-sentiment picker-page">
    <PageHero
      section="市场情绪"
      number="03.2"
      title="板块情绪分布"
      description="按交易日期查看各板块的平均涨幅、涨跌家数及强势标的统计。"
      meta="板块统计"
    />

    <div class="filter-section">
      <div class="filter-item">
        <label>交易日期</label>
        <select v-model="industryDate">
          <option v-for="d in tradeDates" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
      <div class="filter-item filter-actions">
        <button class="btn-primary" @click="handleQuery">查询板块</button>
      </div>
    </div>

    <div v-if="industryLoading" class="chart-loading">加载板块数据中…</div>
    <div v-else class="industry-table-wrapper">
      <table class="stock-table industry-table">
        <thead>
          <tr>
            <th>板块</th>
            <th>股票数</th>
            <th>平均涨幅</th>
            <th>上涨</th>
            <th>下跌</th>
            <th>强势</th>
            <th>总成交额</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in industryList"
            :key="item.industry"
            :class="getIndustryClass(item.avg_pct_chg)"
          >
            <td>{{ item.industry }}</td>
            <td>{{ item.stock_count }}</td>
            <td>{{ item.avg_pct_chg > 0 ? '+' : '' }}{{ item.avg_pct_chg.toFixed(2) }}%</td>
            <td class="up">{{ item.up_count }}</td>
            <td class="down">{{ item.down_count }}</td>
            <td class="strong">{{ item.strong_count }}</td>
            <td>{{ (item.amount_sum / 10000).toFixed(0) }}万</td>
          </tr>
          <tr v-if="!industryLoading && industryList.length === 0">
            <td colspan="7" class="empty">暂无板块数据</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

.filter-actions {
  margin-left: auto;
}

.chart-loading {
  text-align: center;
  padding: 12px;
  font-family: var(--font-body);
  color: var(--text-faint);
  font-size: 13px;
}

.industry-table-wrapper {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border: 1px solid var(--rule);
  border-radius: 4px;
}

.industry-table {
  margin: 0;

  tbody tr {
    transition: background 0.15s;

    &.strong-up {
      background: rgba(34, 197, 94, 0.08);
    }

    &.strong-down {
      background: rgba(239, 68, 68, 0.08);
    }

    &:hover {
      background: var(--bg-tertiary);
    }
  }

  .up {
    color: #22c55e;
  }

  .down {
    color: #ef4444;
  }

  .strong {
    color: #3b82f6;
    font-weight: 600;
  }
}
</style>
