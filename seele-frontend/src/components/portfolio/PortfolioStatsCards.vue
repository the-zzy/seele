<script setup>
defineProps({
  summary: {
    type: Object,
    default: () => ({
      total_invested: 0,
      total_market_value: 0,
      total_pnl: 0,
      total_pnl_pct: 0,
      realized_pnl: 0,
      unrealized_pnl: 0,
      position_count: 0
    })
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
</script>

<template>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">当前总资金</div>
      <div class="stat-value">
        {{ fmt((summary.initial_capital || 0) + (summary.total_pnl || 0)) }}
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">总投入</div>
      <div class="stat-value">
        {{ fmt(summary.total_invested) }}
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">总市值</div>
      <div class="stat-value">
        {{ fmt(summary.total_market_value) }}
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">总盈亏</div>
      <div class="stat-value" :class="pnlClass(summary.total_pnl)">
        {{ fmt(summary.total_pnl) }}
        <span v-if="summary.total_return_pct != null" class="stat-pct" :class="pnlClass(summary.total_return_pct)">
          ({{ summary.total_return_pct > 0 ? '+' : '' }}{{ fmt(summary.total_return_pct) }}%)
        </span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">持仓数量</div>
      <div class="stat-value">
        {{ summary.position_count }}
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 10px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(3, 1fr);
  }

  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;

  &.up {
    color: var(--up);
  }

  &.down {
    color: var(--down);
  }
}

.stat-pct {
  font-size: 13px;
  font-weight: 500;
  margin-left: 6px;
  opacity: 0.9;
}
</style>
