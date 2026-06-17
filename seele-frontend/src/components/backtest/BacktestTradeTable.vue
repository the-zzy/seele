<script setup>
defineProps({
  list: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

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
          <th>股票代码</th>
          <th>股票名称</th>
          <th>类型</th>
          <th>交易日期</th>
          <th class="num">成交价</th>
          <th class="num">股数</th>
          <th class="num">金额</th>
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
    background: var(--accent);
  }

  &.SELL {
    background: var(--up);
  }
}

.buy-row {
  background: rgba(59, 130, 246, 0.04);
}

.sell-row {
  background: rgba(239, 68, 68, 0.04);
}
</style>
