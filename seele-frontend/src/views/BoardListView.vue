<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHero from '@/components/common/PageHero.vue'
import BasePagination from '@/components/common/BasePagination.vue'

const router = useRouter()

const activeTab = ref('industry') // 'industry' | 'board'
const loading = ref(false)

// 申万行业数据
const industryList = ref([])
const industryKeyword = ref('')
const industryTotal = computed(() => filteredIndustryList.value.length)
const industryPageNum = ref(1)
const industryPageSize = ref(50)

// 板块/ETF 数据
const boardList = ref([])
const boardTotal = ref(0)
const boardPageNum = ref(1)
const boardPageSize = ref(50)
const boardFilter = reactive({
  category: '',
  keyword: ''
})

const categoryOptions = [
  { value: '', label: '全部' },
  { value: 'industry', label: '行业板块' },
  { value: 'concept', label: '概念板块' },
  { value: 'etf', label: 'ETF' }
]

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
  return `${sign}${val}%`
}

function formatAmount (val) {
  if (val === null || val === undefined) return '—'
  if (val >= 100000000) return (val / 100000000).toFixed(2) + '亿'
  if (val >= 10000) return (val / 10000).toFixed(0) + '万'
  return val.toFixed(0)
}

// 申万行业过滤后的列表
const filteredIndustryList = computed(() => {
  if (!industryKeyword.value.trim()) return industryList.value
  const kw = industryKeyword.value.trim().toLowerCase()
  return industryList.value.filter(item =>
    item.name?.toLowerCase().includes(kw) ||
    item.industry?.toLowerCase().includes(kw)
  )
})

const pagedIndustryList = computed(() => {
  const start = (industryPageNum.value - 1) * industryPageSize.value
  return filteredIndustryList.value.slice(start, start + industryPageSize.value)
})

async function loadIndustryData () {
  loading.value = true
  try {
    // boardApi 已废弃（后端 board 模块已移除）
    industryList.value = []
    industryPageNum.value = 1
  } catch (error) {
    console.error('加载申万行业数据失败:', error)
    industryList.value = []
  } finally {
    loading.value = false
  }
}

async function loadBoardData () {
  loading.value = true
  try {
    const params = {
      page_num: boardPageNum.value,
      page_size: boardPageSize.value
    }
    if (boardFilter.category) {
      params.category = boardFilter.category
    }
    if (boardFilter.keyword?.trim()) {
      params.keyword = boardFilter.keyword.trim()
    }
    // boardApi 已废弃（后端 board 模块已移除）
    boardList.value = []
    boardTotal.value = 0
  } catch (error) {
    console.error('加载板块列表失败:', error)
    boardList.value = []
    boardTotal.value = 0
  } finally {
    loading.value = false
  }
}

function handleTabChange (tab) {
  activeTab.value = tab
  if (tab === 'industry' && industryList.value.length === 0) {
    loadIndustryData()
  }
  if (tab === 'board' && boardList.value.length === 0) {
    loadBoardData()
  }
}

async function handleIndustrySearch () {
  industryPageNum.value = 1
}

async function handleIndustryReset () {
  industryKeyword.value = ''
  industryPageNum.value = 1
}

async function handleIndustryPageChange (newPage) {
  industryPageNum.value = newPage
}

async function handleIndustryPageSizeChange (newSize) {
  industryPageSize.value = newSize
  industryPageNum.value = 1
}

async function handleBoardSearch () {
  boardPageNum.value = 1
  await loadBoardData()
}

async function handleBoardReset () {
  boardFilter.category = ''
  boardFilter.keyword = ''
  boardPageNum.value = 1
  await loadBoardData()
}

async function handleBoardPageChange (newPage) {
  boardPageNum.value = newPage
  await loadBoardData()
}

async function handleBoardPageSizeChange (newSize) {
  boardPageSize.value = newSize
  boardPageNum.value = 1
  await loadBoardData()
}

function handleRowClick (item) {
  router.push({
    name: 'board-detail',
    params: { code: item.code }
  })
}

onMounted(() => {
  loadIndustryData()
})
</script>

<template>
  <div class="board-list picker-page">
    <PageHero
      section="市场数据"
      number="02"
      title="板块 / ETF"
      description="申万行业实时行情与板块/ETF 基础信息一览。"
      meta="板块索引"
    />

    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'industry' }"
        @click="handleTabChange('industry')"
      >
        申万行业
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'board' }"
        @click="handleTabChange('board')"
      >
        板块 / ETF
      </button>
    </div>

    <!-- 申万行业 -->
    <template v-if="activeTab === 'industry'">
      <div class="filter-section">
        <div class="filter-item">
          <label>关键词</label>
          <input
            v-model="industryKeyword"
            type="text"
            placeholder="行业名称搜索"
            @keyup.enter="handleIndustrySearch"
          >
        </div>
        <div class="filter-item filter-actions">
          <button class="btn-primary" @click="handleIndustrySearch">查询</button>
          <button class="btn-secondary" @click="handleIndustryReset">重置</button>
        </div>
      </div>

      <div class="table-section">
        <div v-if="loading" class="state loading">加载中…</div>
        <div v-else-if="pagedIndustryList.length === 0" class="state empty">暂无数据</div>
        <table v-else class="stock-table">
          <thead>
            <tr>
              <th>行业名称</th>
              <th>股票数</th>
              <th>最新涨幅</th>
              <th>5日涨幅</th>
              <th>10日涨幅</th>
              <th>成交额</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in pagedIndustryList"
              :key="item.industry"
            >
              <td class="name">{{ item.name }}</td>
              <td>{{ item.stock_count }}</td>
              <td :class="getPriceClass(item.latest_pct_chg)">
                {{ formatChg(item.latest_pct_chg) }}
              </td>
              <td :class="getPriceClass(item.chg_5d)">
                {{ formatChg(item.chg_5d) }}
              </td>
              <td :class="getPriceClass(item.chg_10d)">
                {{ formatChg(item.chg_10d) }}
              </td>
              <td>{{ formatAmount(item.amount_sum) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <BasePagination
        v-if="industryTotal > 0"
        :page-num="industryPageNum"
        :page-size="industryPageSize"
        :total="industryTotal"
        @update:page-num="handleIndustryPageChange"
        @update:page-size="handleIndustryPageSizeChange"
      />
    </template>

    <!-- 板块/ETF -->
    <template v-else>
      <div class="filter-section">
        <div class="filter-item">
          <label>类型</label>
          <select v-model="boardFilter.category">
            <option
              v-for="opt in categoryOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>
        <div class="filter-item">
          <label>关键词</label>
          <input
            v-model="boardFilter.keyword"
            type="text"
            placeholder="名称模糊搜索"
            @keyup.enter="handleBoardSearch"
          >
        </div>
        <div class="filter-item filter-actions">
          <button class="btn-primary" @click="handleBoardSearch">查询</button>
          <button class="btn-secondary" @click="handleBoardReset">重置</button>
        </div>
      </div>

      <div class="table-section">
        <div v-if="loading" class="state loading">加载中…</div>
        <div v-else-if="boardList.length === 0" class="state empty">暂无数据</div>
        <table v-else class="stock-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>类型</th>
              <th>最新涨幅</th>
              <th>5日涨幅</th>
              <th>10日涨幅</th>
              <th>交易所</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in boardList"
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
              <td>{{ item.exchange || '—' }}</td>
              <td>{{ item.source || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <BasePagination
        v-if="boardTotal > 0"
        :page-num="boardPageNum"
        :page-size="boardPageSize"
        :total="boardTotal"
        @update:page-num="handleBoardPageChange"
        @update:page-size="handleBoardPageSizeChange"
      />
    </template>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

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

  &:hover {
    color: var(--text-secondary);
  }

  &.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
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
