<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHero from '@/components/common/PageHero.vue'
import BasePagination from '@/components/common/BasePagination.vue'

const route = useRoute()
const router = useRouter()
const code = route.params.code

const board = ref(null)
const dailyList = ref([])
const dailyTotal = ref(0)
const constituents = ref([])
const loading = ref(false)
const dailyLoading = ref(false)
const constituentLoading = ref(false)

const pageNum = ref(1)
const pageSize = ref(50)

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

async function loadBoard () {
  loading.value = true
  try {
    // boardApi 已废弃（后端 board 模块已移除）
    board.value = null
  } catch (error) {
    console.error('加载板块详情失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadDaily () {
  dailyLoading.value = true
  try {
    // boardApi 已废弃（后端 board 模块已移除）
    const res = null
    dailyList.value = res?.list || []
    dailyTotal.value = res?.total || 0
  } catch (error) {
    console.error('加载板块日线失败:', error)
    dailyList.value = []
    dailyTotal.value = 0
  } finally {
    dailyLoading.value = false
  }
}

async function loadConstituents () {
  if (!code) return
  constituentLoading.value = true
  try {
    // boardApi 已废弃（后端 board 模块已移除）
    constituents.value = []
  } catch (error) {
    console.error('加载成分股失败:', error)
    constituents.value = []
  } finally {
    constituentLoading.value = false
  }
}

async function handleDailyPageChange (newPage) {
  pageNum.value = newPage
  await loadDaily()
}

async function handleDailyPageSizeChange (newSize) {
  pageSize.value = newSize
  pageNum.value = 1
  await loadDaily()
}

function goBack () {
  router.push({ name: 'board-list' })
}

function goStock (symbol) {
  router.push({
    name: 'stock-kline',
    params: { symbol }
  })
}

onMounted(() => {
  loadBoard()
  loadDaily()
  loadConstituents()
})
</script>

<template>
  <div class="board-detail picker-page">
    <PageHero
      section="市场数据"
      :number="board?.code || '—'"
      :title="board?.name || '板块详情'"
      :description="board ? `${categoryLabel(board.category)} · 来源 ${board.source || '—'}` : '加载中…'"
      meta="板块详情"
    />

    <div class="detail-toolbar">
      <button class="btn-secondary" @click="goBack">
        ← 返回列表
      </button>
    </div>

    <!-- 最新行情卡片 -->
    <div v-if="board?.latest_daily" class="latest-card">
      <div class="latest-row">
        <div class="latest-item">
          <span class="latest-label">最新收盘</span>
          <span
            class="latest-value"
            :class="getPriceClass(board.latest_daily.pct_chg)"
          >
            {{ board.latest_daily.close != null ? board.latest_daily.close.toFixed(2) : '—' }}
          </span>
        </div>
        <div class="latest-item">
          <span class="latest-label">涨跌幅</span>
          <span
            class="latest-value"
            :class="getPriceClass(board.latest_daily.pct_chg)"
          >
            {{ board.latest_daily.pct_chg != null
              ? (board.latest_daily.pct_chg > 0 ? '+' : '') + board.latest_daily.pct_chg.toFixed(2) + '%'
              : '—' }}
          </span>
        </div>
        <div class="latest-item">
          <span class="latest-label">日期</span>
          <span class="latest-value plain">{{ board.latest_daily.trade_date || '—' }}</span>
        </div>
        <div class="latest-item">
          <span class="latest-label">成交量</span>
          <span class="latest-value plain">{{ board.latest_daily.volume != null ? board.latest_daily.volume.toFixed(0) : '—' }}</span>
        </div>
        <div class="latest-item">
          <span class="latest-label">成交额</span>
          <span class="latest-value plain">{{ board.latest_daily.amount != null ? board.latest_daily.amount.toFixed(0) : '—' }}</span>
        </div>
      </div>
    </div>

    <!-- 成分股 -->
    <div v-if="constituents.length > 0" class="section-block">
      <div class="section-title">
        成分股 ({{ constituents.length }})
      </div>
      <div class="constituent-tags">
        <span
          v-for="c in constituents"
          :key="c.symbol"
          class="constituent-tag"
          @click="goStock(c.symbol)"
        >
          {{ c.name || c.symbol }}
        </span>
      </div>
    </div>

    <!-- 日线数据 -->
    <div class="section-block">
      <div class="section-title">日线数据</div>
      <div class="table-section">
        <div v-if="dailyLoading" class="state loading">加载中…</div>
        <div v-else-if="dailyList.length === 0" class="state empty">暂无日线数据</div>
        <table v-else class="stock-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>开盘</th>
              <th>最高</th>
              <th>最低</th>
              <th>收盘</th>
              <th>成交量</th>
              <th>成交额</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in dailyList"
              :key="item.trade_date"
            >
              <td>{{ item.trade_date }}</td>
              <td>{{ item.open != null ? item.open.toFixed(2) : '—' }}</td>
              <td>{{ item.high != null ? item.high.toFixed(2) : '—' }}</td>
              <td>{{ item.low != null ? item.low.toFixed(2) : '—' }}</td>
              <td :class="getPriceClass(item.pct_chg)">
                {{ item.close != null ? item.close.toFixed(2) : '—' }}
              </td>
              <td>{{ item.volume != null ? item.volume.toFixed(0) : '—' }}</td>
              <td>{{ item.amount != null ? item.amount.toFixed(0) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <BasePagination
        v-if="dailyTotal > 0"
        :page-num="pageNum"
        :page-size="pageSize"
        :total="dailyTotal"
        @update:page-num="handleDailyPageChange"
        @update:page-size="handleDailyPageSizeChange"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

.detail-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.latest-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 14px 18px;
  margin-bottom: 16px;
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

  &.plain {
    color: var(--text-primary);
  }
}

.up {
  color: #22c55e;
}

.down {
  color: #ef4444;
}

.section-block {
  margin-bottom: 16px;
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

.constituent-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.constituent-tag {
  display: inline-block;
  padding: 4px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
}
</style>
