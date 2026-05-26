<script setup>
import { ref, onMounted } from 'vue'
import { indexApi, marketSentimentApi, tradeCalendarApi } from '@/api/stock'
import PageHero from '@/components/common/PageHero.vue'
import { formatNumber } from '@/utils/formatters'

const industryList = ref([])
const industryDate = ref('')
const industryLoading = ref(false)
const indexList = ref([])
const indexLoading = ref(false)

async function loadLatestTradeDate () {
  try {
    const date = await tradeCalendarApi.getLatest()
    if (date) {
      industryDate.value = date
      await loadIndustrySentiment(date)
    }
  } catch (error) {
    console.error('获取最近交易日失败:', error)
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

async function loadIndexList () {
  indexLoading.value = true
  try {
    const res = await indexApi.getIndexList()
    indexList.value = res?.data || []
  } catch (error) {
    console.error('加载指数数据失败:', error)
    indexList.value = []
  } finally {
    indexLoading.value = false
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

function getPriceClass (val) {
  if (val === null || val === undefined) return ''
  const v = parseFloat(val)
  if (v > 0) return 'up'
  if (v < 0) return 'down'
  return ''
}

onMounted(() => {
  loadLatestTradeDate()
  loadIndexList()
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

    <div class="index-cards">
      <div v-if="indexLoading" class="index-loading">加载指数…</div>
      <template v-else>
        <div
          v-for="item in indexList"
          :key="item.symbol"
          class="index-card"
        >
          <div class="index-header">
            <span class="index-name">{{ item.name }}</span>
            <span class="index-source">{{ item.data_source === 'akshare_spot' ? '实时' : '缓存' }}</span>
          </div>
          <div class="index-close" :class="getPriceClass(item.latest_pct_chg)">
            {{ item.latest_close != null ? formatNumber(item.latest_close) : '-' }}
          </div>
          <div class="index-pct" :class="getPriceClass(item.latest_pct_chg)">
            {{ item.latest_pct_chg != null ? (item.latest_pct_chg > 0 ? '+' : '') + item.latest_pct_chg + '%' : '-' }}
          </div>
          <div class="index-date">{{ item.latest_trade_date || '-' }}</div>
        </div>
      </template>
      <button class="index-refresh" title="刷新指数" @click="loadIndexList">
        ↻
      </button>
    </div>

    <div class="filter-section">
      <div class="filter-item">
        <label>交易日期</label>
        <input v-model="industryDate" type="date" />
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

.index-cards {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.index-loading {
  padding: 12px;
  font-size: 13px;
  color: var(--text-faint);
}

.index-card {
  flex: 1;
  min-width: 140px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.index-name {
  font-size: 12px;
  color: var(--text-secondary);
}

.index-source {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.index-refresh {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-tertiary);
    border-color: var(--border-focus);
    color: var(--text-primary);
  }
}

.index-close {
  font-size: 18px;
  font-weight: 600;
  font-family: var(--font-mono);
}

.index-pct {
  font-size: 13px;
  font-family: var(--font-mono);
}

.index-date {
  font-size: 11px;
  color: var(--text-muted);
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
