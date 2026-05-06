<script setup>
import { useRouter } from 'vue-router'
import { stockDailyApi } from '@/api/stock'
import { useStockPicker } from '@/composables/useStockPicker'
import BreakoutPickerFilter from '@/components/stock/BreakoutPickerFilter.vue'
import BreakoutPickerTable from '@/components/stock/BreakoutPickerTable.vue'
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
  fetcher: stockDailyApi.getBreakoutPicker,
  defaultSortField: 'pct_chg',
  defaultSortOrder: 'desc',
  serverSort: false,
  defaultPageSize: 20,
  fetchPageSize: 100
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
      number="03.5"
      title="倍量突破"
      description="阳线确认 + 倍量异动 + 平台突破 + 站上年线，四个信号共振。"
      meta="平台突破"
    />

    <BreakoutPickerFilter @search="search" />

    <div class="result-bar">共 {{ total }} 只</div>

    <BreakoutPickerTable
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
