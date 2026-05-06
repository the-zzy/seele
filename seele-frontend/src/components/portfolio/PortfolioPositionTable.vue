<script setup>
defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
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
</script>

<template>
  <div class="table-section">
    <div class="section-title">
      当前持仓
      <span v-if="list.length" class="section-count">{{ list.length }} 只</span>
    </div>
    <div class="table-wrap">
      <table class="stock-table">
        <thead>
          <tr>
            <th>股票代码</th>
            <th>股票名称</th>
            <th class="num">持仓股数</th>
            <th class="num">平均成本</th>
            <th class="num">最新价</th>
            <th class="num">市值</th>
            <th class="num">浮动盈亏</th>
            <th class="num">盈亏比例</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="empty">加载中...</td>
          </tr>
          <tr v-else-if="!list.length">
            <td colspan="8" class="empty">暂无持仓</td>
          </tr>
          <tr v-for="item in list" :key="item.symbol">
            <td class="mono">{{ item.symbol }}</td>
            <td>{{ item.name }}</td>
            <td class="num">{{ item.quantity.toLocaleString() }}</td>
            <td class="num">{{ fmt(item.avg_cost) }}</td>
            <td class="num">{{ fmt(item.current_price) }}</td>
            <td class="num">{{ fmt(item.market_value) }}</td>
            <td class="num" :class="pnlClass(item.unrealized_pnl)">
              {{ fmt(item.unrealized_pnl) }}
            </td>
            <td class="num" :class="pnlClass(item.unrealized_pnl_pct)">
              {{ fmt(item.unrealized_pnl_pct) }}%
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th, td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
  }

  th {
    background: var(--bg-tertiary);
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 500;
    position: sticky;
    top: 0;
    z-index: 1;
  }

  td {
    color: var(--text-secondary);
  }

  tr:hover td {
    background: var(--bg-tertiary);
  }

  .num {
    text-align: right;
    font-family: var(--font-mono);
  }

  .mono {
    font-family: var(--font-mono);
  }

  .up {
    color: var(--up);
  }

  .down {
    color: var(--down);
  }

  .empty {
    text-align: center;
    color: var(--text-muted);
    padding: 28px;
  }
}
</style>
