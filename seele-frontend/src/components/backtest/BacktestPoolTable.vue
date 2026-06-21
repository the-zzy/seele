<script setup>
const props = defineProps({
  list: {
    type: Array,
    default: () => []
  },
  sortField: {
    type: String,
    default: 'score'
  },
  sortOrder: {
    type: String,
    default: 'desc'
  }
})

const emit = defineEmits(['sort'])

function onSort (field) {
  emit('sort', field)
}

function getSortIcon (field) {
  if (field !== props.sortField) return '⇅'
  return props.sortOrder === 'asc' ? '▲' : '▼'
}

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="table-wrap">
    <div v-if="!list.length" class="state empty">当日无买入池子</div>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th class="sortable" @click="onSort('symbol')"><span class="th-label">股票代码</span><span class="sort-icon">{{ getSortIcon('symbol') }}</span></th>
          <th class="sortable" @click="onSort('name')"><span class="th-label">股票名称</span><span class="sort-icon">{{ getSortIcon('name') }}</span></th>
          <th class="sortable num" @click="onSort('layer')"><span class="th-label">层</span><span class="sort-icon">{{ getSortIcon('layer') }}</span></th>
          <th class="sortable num" @click="onSort('close')"><span class="th-label">收盘价</span><span class="sort-icon">{{ getSortIcon('close') }}</span></th>
          <th class="sortable num" @click="onSort('ma5')"><span class="th-label">MA5</span><span class="sort-icon">{{ getSortIcon('ma5') }}</span></th>
          <th class="sortable num" @click="onSort('ma10')"><span class="th-label">MA10</span><span class="sort-icon">{{ getSortIcon('ma10') }}</span></th>
          <th class="sortable num" @click="onSort('ma20')"><span class="th-label">MA20</span><span class="sort-icon">{{ getSortIcon('ma20') }}</span></th>
          <th class="sortable num" @click="onSort('score')"><span class="th-label">评分</span><span class="sort-icon">{{ getSortIcon('score') }}</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in list" :key="item.symbol" class="data-row">
          <td class="mono">{{ item.symbol }}</td>
          <td>{{ item.name }}</td>
          <td class="num">{{ item.layer }}</td>
          <td class="num">{{ fmt(item.close) }}</td>
          <td class="num">{{ fmt(item.ma5) }}</td>
          <td class="num">{{ fmt(item.ma10) }}</td>
          <td class="num">{{ fmt(item.ma20) }}</td>
          <td class="num">{{ item.score?.total ?? '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
}

.stock-table {
  min-width: 560px;
  width: 100%;

  th.sortable {
    cursor: pointer;
    user-select: none;

    &:hover {
      color: var(--text-primary);
    }
  }

  .th-label {
    margin-right: 4px;
  }

  .sort-icon {
    font-size: 10px;
    color: var(--text-muted);
  }
}

.state {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
