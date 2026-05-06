<script setup>
import { useRouter } from 'vue-router'
import { stockDailyApi } from '@/api/stock'
import { useStockPicker } from '@/composables/useStockPicker'
import ShrinkingPickerFilter from '@/components/stock/ShrinkingPickerFilter.vue'
import ShrinkingPickerTable from '@/components/stock/ShrinkingPickerTable.vue'
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
  fetcher: stockDailyApi.getShrinkingVolume,
  defaultSortField: 'consecutive_days',
  defaultSortOrder: 'desc',
  serverSort: false,
  defaultPageSize: 20,
  fetchPageSize: 500
})

function handleRowDblClick (item) {
  if (!item.symbol) return
  router.push({
    name: 'stock-kline',
    params: { symbol: item.symbol },
    query: { name: item.name || item.stock_name || '' }
  })
}
</script>

<template>
  <div class="picker-page">
    <PageHero
      section="选股策略"
      number="03.4"
      title="缩量选股"
      description="连续多日缩量整理，捕捉资金沉淀后的潜在启动信号。"
      meta="资金沉淀"
    />

    <ShrinkingPickerFilter @search="search" />

    <div class="result-bar">共 {{ total }} 条结果</div>

    <ShrinkingPickerTable
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
