<script setup>
const props = defineProps({
  list: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  sortField: {
    type: String,
    default: 'trade_date'
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
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="!list.length" class="state empty">暂无交易记录</div>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th class="sortable" @click="onSort('symbol')"><span class="th-label">股票代码</span><span class="sort-icon">{{ getSortIcon('symbol') }}</span></th>
          <th class="sortable" @click="onSort('name')"><span class="th-label">股票名称</span><span class="sort-icon">{{ getSortIcon('name') }}</span></th>
          <th class="sortable" @click="onSort('trade_type')"><span class="th-label">类型</span><span class="sort-icon">{{ getSortIcon('trade_type') }}</span></th>
          <th class="sortable" @click="onSort('trade_date')"><span class="th-label">交易日期</span><span class="sort-icon">{{ getSortIcon('trade_date') }}</span></th>
          <th class="sortable num" @click="onSort('price')"><span class="th-label">成交价</span><span class="sort-icon">{{ getSortIcon('price') }}</span></th>
          <th class="sortable num" @click="onSort('quantity')"><span class="th-label">股数</span><span class="sort-icon">{{ getSortIcon('quantity') }}</span></th>
          <th class="sortable num" @click="onSort('amount')"><span class="th-label">金额</span><span class="sort-icon">{{ getSortIcon('amount') }}</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in list"
          :key="item.id"
          class="data-row"
          :class="item.trade_type === 'BUY' ? 'buy-row' : 'sell-row'"
        >
          <td class="mono">{{ item.symbol }}</td>
          <td>{{ item.name }}</td>
          <td>
            <span class="tag" :class="item.trade_type">{{ item.trade_type === 'BUY' ? '买入' : '卖出' }}</span>
          </td>
          <td>{{ item.trade_date }}</td>
          <td class="num">{{ fmt(item.price) }}</td>
          <td class="num">{{ item.quantity }}</td>
          <td class="num">{{ fmt(item.amount) }}</td>
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
  min-width: 640px;
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

.tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;

  &.BUY {
    background: var(--up);
  }

  &.SELL {
    background: var(--accent);
  }
}

.buy-row {
  background: rgba(239, 68, 68, 0.04);
}

.sell-row {
  background: rgba(59, 130, 246, 0.04);
}
</style>
