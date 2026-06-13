<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { financialApi } from '@/api/financial'
import FinancialListTable from '@/components/stock/FinancialListTable.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const loading = ref(false)
const stockList = ref([])
const total = ref(0)
const pageNum = ref(1)
const pageSize = ref(10)

let filterForm = reactive({
  symbol: '',
  name: '',
  industry: '',
  roe_min: '',
  roe_max: '',
  gross_profit_ratio_min: '',
  gross_profit_ratio_max: ''
})

const sortField = ref('roe')
const sortOrder = ref('desc')

function handleSort (field) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'desc'
  }
  loadData()
}

function buildParams () {
  const params = {
    page_num: pageNum.value,
    page_size: pageSize.value,
    sort_field: sortField.value,
    sort_order: sortOrder.value
  }
  if (filterForm.symbol?.trim()) {
    params.symbol = filterForm.symbol.trim()
  }
  if (filterForm.name?.trim()) {
    params.name = filterForm.name.trim()
  }
  if (filterForm.industry?.trim()) {
    params.industry = filterForm.industry.trim()
  }
  if (filterForm.roe_min !== '') {
    params.roe_min = Number(filterForm.roe_min)
  }
  if (filterForm.roe_max !== '') {
    params.roe_max = Number(filterForm.roe_max)
  }
  if (filterForm.gross_profit_ratio_min !== '') {
    params.gross_profit_ratio_min = Number(filterForm.gross_profit_ratio_min)
  }
  if (filterForm.gross_profit_ratio_max !== '') {
    params.gross_profit_ratio_max = Number(filterForm.gross_profit_ratio_max)
  }
  return params
}

async function loadData () {
  loading.value = true
  try {
    const res = await financialApi.getList(buildParams())
    stockList.value = res?.list || []
    total.value = res?.total || 0
  } catch (error) {
    console.error('加载财务指标失败:', error)
    stockList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleSearch () {
  pageNum.value = 1
  await loadData()
}

async function handleReset () {
  filterForm.symbol = ''
  filterForm.name = ''
  filterForm.industry = ''
  filterForm.roe_min = ''
  filterForm.roe_max = ''
  filterForm.gross_profit_ratio_min = ''
  filterForm.gross_profit_ratio_max = ''
  sortField.value = 'roe'
  sortOrder.value = 'desc'
  pageNum.value = 1
  await loadData()
}

async function handlePageChange (newPage) {
  pageNum.value = newPage
  await loadData()
}

async function handlePageSizeChange (newSize) {
  pageSize.value = newSize
  pageNum.value = 1
  await loadData()
}

function handleRowDblClick (item) {
  router.push({
    name: 'stock-financial',
    params: { symbol: item.symbol },
    query: { name: item.name }
  })
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="financial-list page">
    <PageHero
      section="基本面"
      number="02"
      title="财务指标"
      description="沪深主板核心财务数据一览：盈利能力、成长性与偿债能力。"
      meta="财务维度"
    />

    <div class="filter-section">
      <div class="filter-fields">
        <label class="field">
          <span class="field-label">代码</span>
          <input v-model="filterForm.symbol" type="text" placeholder="600519" @keyup.enter="handleSearch" />
        </label>
        <label class="field">
          <span class="field-label">名称</span>
          <input v-model="filterForm.name" type="text" placeholder="输入名称" @keyup.enter="handleSearch" />
        </label>
        <label class="field">
          <span class="field-label">行业</span>
          <input v-model="filterForm.industry" type="text" placeholder="输入行业" @keyup.enter="handleSearch" />
        </label>
        <label class="field range">
          <span class="field-label">ROE</span>
          <input v-model="filterForm.roe_min" type="number" placeholder="min" @keyup.enter="handleSearch" />
          <span class="range-sep">~</span>
          <input v-model="filterForm.roe_max" type="number" placeholder="max" @keyup.enter="handleSearch" />
        </label>
        <label class="field range">
          <span class="field-label">毛利率</span>
          <input v-model="filterForm.gross_profit_ratio_min" type="number" placeholder="min" @keyup.enter="handleSearch" />
          <span class="range-sep">~</span>
          <input v-model="filterForm.gross_profit_ratio_max" type="number" placeholder="max" @keyup.enter="handleSearch" />
        </label>
      </div>

      <div class="filter-actions">
        <button class="btn-link" @click="handleReset">重置</button>
        <button class="btn-primary" @click="handleSearch">检索</button>
      </div>
    </div>

    <FinancialListTable
      :list="stockList"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :loading="loading"
      @sort="handleSort"
      @row-dblclick="handleRowDblClick"
    />

    <BasePagination
      v-if="total > 0"
      :page-num="pageNum"
      :page-size="pageSize"
      :total="total"
      @update:page-num="handlePageChange"
      @update:page-size="handlePageSizeChange"
    />
  </div>
</template>

<style scoped lang="scss">
.financial-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
}

.filter-section {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.filter-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  flex: 1;
}

.field {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 140px;
  flex: 1;

  .field-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
    width: 36px;
    text-align: right;
  }

  input {
    flex: 1;
    padding: 5px 10px;
    background: var(--bg-input);
    border: 1px solid var(--rule);
    border-radius: 5px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-primary);
    transition: border-color 0.2s;
    min-width: 0;

    &:focus {
      outline: none;
      border-color: var(--border-focus);
    }

    &::placeholder {
      color: var(--text-muted);
    }
  }
}

.field.range {
  min-width: 200px;

  input {
    flex: 1;
    min-width: 0;
  }

  .range-sep {
    color: var(--text-muted);
    font-size: 11px;
    flex-shrink: 0;
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-primary {
  padding: 5px 14px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  transition: background 0.2s;

  &:hover { background: var(--accent-hover); }
}

.btn-link {
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  padding: 5px 10px;
  border-radius: 5px;
  transition: all 0.2s;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
}

@media (max-width: 768px) {
  .filter-section {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .filter-fields {
    flex-direction: column;
    gap: 8px;
  }

  .field {
    min-width: 0;
    width: 100%;

    .field-label {
      width: auto;
      text-align: left;
    }

    input {
      width: 100%;
      box-sizing: border-box;
      min-height: var(--touch-target);
    }
  }

  .field.range {
    min-width: 0;

    input {
      flex: 1;
    }
  }

  .filter-actions {
    width: 100%;
    justify-content: stretch;

    button {
      flex: 1;
      min-height: var(--touch-target);
    }
  }
}
</style>
