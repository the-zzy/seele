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
  }
})

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
  return result
})
</script>

<template>
  <div class="table-wrap">
    <div v-if="!items.length" class="state empty">当前无持仓</div>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th>股票代码</th>
          <th>股票名称</th>
          <th class="num">持仓股数</th>
          <th class="num">平均成本</th>
          <th class="num">收盘价</th>
          <th class="num">市值</th>
          <th class="num">浮动盈亏</th>
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
}

.state {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
