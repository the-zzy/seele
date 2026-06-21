<script setup>
import { computed } from 'vue'

const props = defineProps({
  positions: {
    type: Object,
    default: () => ({})
  },
  closeMap: {
    type: Object,
    default: () => ({})
  },
  sortField: {
    type: String,
    default: 'symbol'
  },
  sortOrder: {
    type: String,
    default: 'asc'
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

function pnlClass (v) {
  if (v == null) return ''
  const n = Number(v)
  if (n > 0) return 'up'
  if (n < 0) return 'down'
  return ''
}

const items = computed(() => {
  const result = []
  for (const symbol in props.positions) {
    const p = props.positions[symbol]
    const close = props.closeMap[symbol]
    const mv = close != null ? close * p.quantity : 0
    const unrealized = mv - p.cost
    const unrealizedPct = p.cost > 0 ? unrealized / p.cost * 100 : 0
    result.push({
      symbol,
      name: p.name,
      quantity: p.quantity,
      avg_cost: p.avg_cost,
      close,
      market_value: mv,
      unrealized,
      unrealized_pct: unrealizedPct
    })
  }

  const field = props.sortField
  const order = props.sortOrder
  const multiplier = order === 'desc' ? -1 : 1

  return result.sort((a, b) => {
    const va = a[field]
    const vb = b[field]

    if (va == null && vb == null) return 0
    if (va == null) return 1 * multiplier
    if (vb == null) return -1 * multiplier

    if (typeof va === 'number' && typeof vb === 'number') {
      return (va - vb) * multiplier
    }

    return String(va).localeCompare(String(vb), 'zh-CN') * multiplier
  })
})
</script>

<template>
  <div class="table-wrap">
    <div v-if="!items.length" class="state empty">当前无持仓</div>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th class="sortable" @click="onSort('symbol')"><span class="th-label">股票代码</span><span class="sort-icon">{{ getSortIcon('symbol') }}</span></th>
          <th class="sortable" @click="onSort('name')"><span class="th-label">股票名称</span><span class="sort-icon">{{ getSortIcon('name') }}</span></th>
          <th class="sortable num" @click="onSort('quantity')"><span class="th-label">持仓股数</span><span class="sort-icon">{{ getSortIcon('quantity') }}</span></th>
          <th class="sortable num" @click="onSort('avg_cost')"><span class="th-label">平均成本</span><span class="sort-icon">{{ getSortIcon('avg_cost') }}</span></th>
          <th class="sortable num" @click="onSort('close')"><span class="th-label">收盘价</span><span class="sort-icon">{{ getSortIcon('close') }}</span></th>
          <th class="sortable num" @click="onSort('market_value')"><span class="th-label">市值</span><span class="sort-icon">{{ getSortIcon('market_value') }}</span></th>
          <th class="sortable num" @click="onSort('unrealized')"><span class="th-label">浮动盈亏</span><span class="sort-icon">{{ getSortIcon('unrealized') }}</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.symbol" class="data-row">
          <td class="mono">{{ item.symbol }}</td>
          <td>{{ item.name }}</td>
          <td class="num">{{ item.quantity }}</td>
          <td class="num">{{ fmt(item.avg_cost) }}</td>
          <td class="num">{{ fmt(item.close) }}</td>
          <td class="num">{{ fmt(item.market_value) }}</td>
          <td class="num" :class="pnlClass(item.unrealized)">
            {{ fmt(item.unrealized) }} ({{ item.unrealized_pct > 0 ? '+' : '' }}{{ fmt(item.unrealized_pct) }}%)
          </td>
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
</style>
