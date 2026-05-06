<script setup>
import { useRouter } from 'vue-router'
import { stockDailyApi } from '@/api/stock'
import { useStockPicker } from '@/composables/useStockPicker'
import RangePickerFilter from '@/components/stock/RangePickerFilter.vue'
import RangePickerTable from '@/components/stock/RangePickerTable.vue'
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
  fetcher: stockDailyApi.getRangePicker,
  defaultSortField: 'bb_width',
  defaultSortOrder: 'asc',
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
      number="03.2"
      title="震荡选股"
      description="布林带收口 + RSI 中性 + 均线缠绕 + 缩量 + 振幅适中，识别低波动整理形态。"
      meta="低波形态"
    />

    <RangePickerFilter @search="search" />

    <div class="result-bar">共 {{ total }} 只</div>

    <RangePickerTable
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
