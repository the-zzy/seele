<script setup>
const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'roe' },
  sortOrder: { type: String, default: 'desc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const columns = [
  { key: 'symbol', label: '股票代码', align: 'left' },
  { key: 'name', label: '股票名称', align: 'left' },
  { key: 'industry', label: '所属行业', align: 'left' },
  { key: 'market', label: '市场板块', align: 'center' },
  { key: 'roe', label: 'ROE', align: 'right' },
  { key: 'gross_profit_ratio', label: '毛利率', align: 'right' },
  { key: 'net_profit_ratio', label: '净利率', align: 'right' },
  { key: 'net_profit_yoy', label: '净利润同比', align: 'right' },
  { key: 'revenue_yoy', label: '营收同比', align: 'right' },
  { key: 'eps', label: 'EPS', align: 'right' },
  { key: 'debt_ratio', label: '资产负债率', align: 'right' }
]

function onSort (field) {
  emit('sort', field)
}

function getSortIconForField (field) {
  if (field !== props.sortField) return '⇅'
  return props.sortOrder === 'asc' ? '▲' : '▼'
}

function extractCodeNum (symbol) {
  if (!symbol) return ''
  const match = symbol.match(/\d+/)
  return match ? match[0] : symbol
}

function formatPercent (val) {
  if (val == null || val === undefined) return '—'
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

function getYoyClass (val) {
  if (val == null) return ''
  return Number(val) >= 0 ? 'up' : 'down'
}

function onRowDblClick (item) {
  emit('row-dblclick', item)
}
</script>

<template>
  <div class="table-section">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">暂无数据</div>
    <table v-else class="stock-table">
      <colgroup>
        <col style="width: 8%">
        <col style="width: 10%">
        <col style="width: 12%">
        <col style="width: 8%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 8%">
        <col style="width: 8%">
        <col style="width: 6%">
        <col style="width: 9%">
      </colgroup>
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="sortable"
            :class="{ 'th-left': col.align === 'left', 'th-center': col.align === 'center' }"
            @click="onSort(col.key)"
          >
            <span class="th-label">{{ col.label }}</span>
            <span class="sort-icon">{{ getSortIconForField(col.key) }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in list"
          :key="item.symbol"
          class="data-row"
          @dblclick="onRowDblClick(item)"
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td class="td-left">{{ item.industry || '—' }}</td>
          <td class="td-center">{{ item.market || '—' }}</td>
          <td>{{ item.roe != null ? `${item.roe.toFixed(2)}%` : '—' }}</td>
          <td>{{ item.gross_profit_ratio != null ? `${item.gross_profit_ratio.toFixed(2)}%` : '—' }}</td>
          <td>{{ item.net_profit_ratio != null ? `${item.net_profit_ratio.toFixed(2)}%` : '—' }}</td>
          <td :class="getYoyClass(item.net_profit_yoy)">{{ formatPercent(item.net_profit_yoy) }}</td>
          <td :class="getYoyClass(item.revenue_yoy)">{{ formatPercent(item.revenue_yoy) }}</td>
          <td>{{ item.eps != null ? item.eps.toFixed(2) : '—' }}</td>
          <td>{{ item.debt_ratio != null ? `${item.debt_ratio.toFixed(2)}%` : '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.table-section {
  overflow-x: auto;
}

.stock-table {
  min-width: 960px;
}
</style>
