<script setup>
import { useRouter } from 'vue-router'
import { stockDailyApi } from '@/api/stock'
import { useStockPicker } from '@/composables/useStockPicker'
import TrendPickerFilter from '@/components/stock/TrendPickerFilter.vue'
import TrendPickerTable from '@/components/stock/TrendPickerTable.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const {
  loading,
  total,
  pageNum,
  pageSize,
  sortField,
  sortOrder,
  displayList,
  search,
  handleSort,
  handlePageChange,
  handlePageSizeChange
} = useStockPicker({
  fetcher: stockDailyApi.getTrendPicker,
  defaultSortField: 'pct_chg',
  defaultSortOrder: 'desc',
  serverSort: true,
  defaultPageSize: 20
})

function handleRowDblClick (item) {
  if (!item.symbol) return
  router.push({
    name: 'stock-kline',
    params: { symbol: item.symbol },
    query: { name: item.name || '' }
  })
}
</script>

<template>
  <div class="picker-page">
    <PageHero
      section="选股策略"
      number="03.3"
      title="趋势选股"
      description="均线多头排列 + MACD 金叉 + RSI 健康区间 + 放量，捕捉趋势启动信号。"
      meta="趋势启动"
    />

    <TrendPickerFilter @search="search" />

    <div class="result-bar">共 {{ total }} 只</div>

    <TrendPickerTable
      :items="displayList"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :loading="loading"
      :total="total"
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
@import '~@/styles/picker';
</style>
