<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockBasicApi } from '@/api/stock'
import StockBasicFilter from '@/components/stock/StockBasicFilter.vue'
import StockBasicTable from '@/components/stock/StockBasicTable.vue'
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
  area: ''
})

const sortField = ref('symbol')
const sortOrder = ref('asc')

function handleSort (field) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'asc'
  }
  loadData()
}

async function loadData () {
  loading.value = true
  try {
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
    if (filterForm.area?.trim()) {
      params.area = filterForm.area.trim()
    }

    const res = await stockBasicApi.pageQuery(params)
    const list = (res?.list || []).map(item => ({
      id: item.id,
      symbol: item.symbol,
      name: item.name,
      industry: item.industry,
      area: item.area,
      market: item.market,
      listDate: item.list_date,
      roe: item.roe,
      grossProfitRatio: item.gross_profit_ratio,
      netProfitRatio: item.net_profit_ratio,
      netProfitYoy: item.net_profit_yoy,
      revenueYoy: item.revenue_yoy
    }))

    // 批量加载所属板块（boardApi 已废弃，后端 board 模块已移除）
    for (const item of list) {
      item.boards = null
    }

    stockList.value = list
    total.value = res?.total || 0
  } catch (error) {
    console.error('加载股票基本信息失败:', error)
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
  filterForm.area = ''
  sortField.value = 'symbol'
  sortOrder.value = 'asc'
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
  <div class="stock-basic page">
    <PageHero
      section="基本面"
      number="01"
      title="股票基本信息"
      description="A 股标的索引：代码、名称、行业、地域、上市板块与时间。其他章节的数据均以此为锚点。"
      meta="底层维度"
    />

    <StockBasicFilter
      v-model="filterForm"
      @search="handleSearch"
      @reset="handleReset"
    />

    <StockBasicTable
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
.stock-basic {
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
</style>
