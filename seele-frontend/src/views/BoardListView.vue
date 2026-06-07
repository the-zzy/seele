<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHero from '@/components/common/PageHero.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import { boardApi, tradeCalendarApi } from '@/api/stock'

const router = useRouter()

const activeTab = ref('industry')
const loading = ref(false)
const latestTradeDate = ref('')
const queryDate = ref('')

// 三个标签页共用的配置
const TABS = [
  { key: 'industry', label: '行业板块', category: 'industry', count: 0 },
  { key: 'concept', label: '概念板块', category: 'concept', count: 0 },
  { key: 'etf', label: 'ETF', category: 'etf', count: 0 },
]

// 各标签页数据
const tabData = ref({
  industry: { list: [], total: 0, pageNum: 1, pageSize: 10 },
  concept: { list: [], total: 0, pageNum: 1, pageSize: 10 },
  etf: { list: [], total: 0, pageNum: 1, pageSize: 10 },
})
const keyword = ref('')

function categoryLabel (category) {
  const map = { industry: '行业', concept: '概念', etf: 'ETF' }
  return map[category] || category
}

function categoryClass (category) {
  return `tag-${category}`
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

function formatDate (d) {
  if (!d) return '—'
  const m = String(d).match(/^(\d{4})-?(\d{2})-?(\d{2})/)
  if (m) return `${m[1]}-${m[2]}-${m[3]}`
  return String(d)
}

function currentTab () {
  return tabData.value[activeTab.value]
}

async function loadTabData (tabKey) {
  const tab = tabData.value[tabKey]
  if (!tab) return
  loading.value = true
  try {
    const params = {
      page_num: tab.pageNum,
      page_size: tab.pageSize,
      category: tabKey,
    }
    if (keyword.value.trim()) {
      params.keyword = keyword.value.trim()
    }
    if (queryDate.value) {
      params.trade_date = queryDate.value
    }
    const res = await boardApi.getList(params)
    tab.list = res?.list || []
    tab.total = res?.total || 0
  } catch (error) {
    console.error(`加载${tabKey}数据失败:`, error)
    tab.list = []
  } finally {
    loading.value = false
  }
}

function handleTabChange (tabKey) {
  activeTab.value = tabKey
  const tab = tabData.value[tabKey]
  if (tab && tab.list.length === 0) {
    loadTabData(tabKey)
  }
}

function handleSearch () {
  const tab = currentTab()
  if (tab) {
    tab.pageNum = 1
    loadTabData(activeTab.value)
  }
}

function handleReset () {
  keyword.value = ''
  const tab = currentTab()
  if (tab) {
    tab.pageNum = 1
    loadTabData(activeTab.value)
  }
}

function handlePageChange (newPage) {
  const tab = currentTab()
  if (tab) {
    tab.pageNum = newPage
    loadTabData(activeTab.value)
  }
}

function handlePageSizeChange (newSize) {
  const tab = currentTab()
  if (tab) {
    tab.pageSize = newSize
    tab.pageNum = 1
    loadTabData(activeTab.value)
  }
}

function handleDateQuery () {
  // 重新加载当前标签页，带上日期参数
  const tab = currentTab()
  if (tab) {
    tab.pageNum = 1
    loadTabData(activeTab.value)
  }
}

function handleRowClick (item) {
  router.push({
    name: 'board-detail',
    params: { code: item.code }
  })
}

onMounted(async () => {
  try {
    const res = await tradeCalendarApi.getLatest()
    if (res) {
      latestTradeDate.value = formatDate(res)
      queryDate.value = formatDate(res)
    }
  } catch (_) { /* ignore */ }
  loadTabData('industry')
})
</script>

<template>
  <div class="board-list picker-page">
    <PageHero
      section="市场数据"
      number="02"
      title="板块 / ETF"
      :description="latestTradeDate ? `同花顺行业/概念板块 + ETF 行情 · 数据截至 ${latestTradeDate}` : '同花顺行业/概念板块 + ETF 行情'"
      meta="板块索引"
    />

    <!-- 全局日期查询 -->
    <div class="date-filter">
      <label class="date-label">交易日</label>
      <input
        v-model="queryDate"
        type="date"
        class="date-input"
        @change="handleDateQuery"
      />
      <span class="date-hint">切换日期查看历史行情</span>
    </div>

    <!-- 标签页 -->
    <div class="tab-bar">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab-btn"
        :class="{ active: activeTab === t.key }"
        @click="handleTabChange(t.key)"
      >
        {{ t.label }}
        <span v-if="currentTab()?.total > 0" class="tab-count">{{ currentTab().total }}</span>
      </button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-section">
      <div class="filter-item">
        <label>关键词</label>
        <input
          v-model="keyword"
          type="text"
          placeholder="名称模糊搜索"
          @keyup.enter="handleSearch"
        />
      </div>
      <div class="filter-item filter-actions">
        <button class="btn-primary" @click="handleSearch">查询</button>
        <button class="btn-secondary" @click="handleReset">重置</button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-section">
      <div v-if="loading" class="state loading">加载中…</div>
      <div v-else-if="!currentTab()?.list?.length" class="state empty">暂无数据</div>
      <table v-else class="stock-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>类型</th>
            <th>最新涨幅</th>
            <th>5日涨幅</th>
            <th>10日涨幅</th>
            <th>成交额</th>
            <th>成分股</th>
            <th>来源</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in currentTab()?.list"
            :key="item.code"
            class="data-row"
            @click="handleRowClick(item)"
          >
            <td class="code">{{ item.code }}</td>
            <td class="name">{{ item.name }}</td>
            <td>
              <span class="category-tag" :class="categoryClass(item.category)">
                {{ categoryLabel(item.category) }}
              </span>
            </td>
            <td :class="getPriceClass(item.latest_pct_chg)">
              {{ formatChg(item.latest_pct_chg) }}
            </td>
            <td :class="getPriceClass(item.chg_5d)">
              {{ formatChg(item.chg_5d) }}
            </td>
            <td :class="getPriceClass(item.chg_10d)">
              {{ formatChg(item.chg_10d) }}
            </td>
            <td>{{ formatAmount(item.amount) }}</td>
            <td class="constituent">{{ item.constituent_count || 0 }}</td>
            <td>{{ item.source || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination
      v-if="(currentTab()?.total || 0) > 0"
      :page-num="currentTab()?.pageNum || 1"
      :page-size="currentTab()?.pageSize || 50"
      :total="currentTab()?.total || 0"
      @update:page-num="handlePageChange"
      @update:page-size="handlePageSizeChange"
    />
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

.date-filter {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
}

.date-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  font-family: var(--font-display);
}

.date-input {
  padding: 4px 8px;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-mono);
}

.date-hint {
  font-size: 11px;
  color: var(--text-faint);
}

.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--rule);
}

.tab-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  position: relative;

  &:hover {
    color: var(--text-secondary);
  }

  &.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
}

.tab-count {
  display: inline-block;
  margin-left: 6px;
  padding: 0 6px;
  font-size: 11px;
  line-height: 18px;
  border-radius: 10px;
  background: var(--bg-tertiary);
  color: var(--text-faint);
  font-family: var(--font-mono);
}

.category-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-family: var(--font-mono);
}

.tag-industry {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.tag-concept {
  background: rgba(168, 85, 247, 0.12);
  color: #a855f7;
}

.tag-etf {
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
}

.data-row {
  cursor: pointer;

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
</style>
