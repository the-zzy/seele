<script setup>
defineProps({
  run: {
    type: Object,
    default: () => ({})
  },
  snapshot: {
    type: Object,
    default: () => null
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
      <div class="stat-label">当前操作日</div>
      <div class="stat-value">{{ run.current_date || '-' }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">总资产</div>
      <div class="stat-value">{{ fmt(snapshot?.total_asset) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">现金</div>
      <div class="stat-value">{{ fmt(snapshot?.cash) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">总市值</div>
      <div class="stat-value">{{ fmt(snapshot?.total_market_value) }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">累计盈亏</div>
      <div class="stat-value" :class="pnlClass(snapshot?.cumulative_pnl)">
        {{ fmt(snapshot?.cumulative_pnl) }}
        <span v-if="run.total_return_pct != null" class="stat-pct" :class="pnlClass(run.total_return_pct)">
          ({{ run.total_return_pct > 0 ? '+' : '' }}{{ fmt(run.total_return_pct) }}%)
        </span>
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
