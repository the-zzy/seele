<template>
  <div class="tool-call-card" :class="{ 'tool-write': isWrite }">
    <div class="tool-header" @click="expanded = !expanded">
      <span class="tool-icon">{{ isWrite ? '⚠' : '🔍' }}</span>
      <span class="tool-name">{{ displayName }}</span>
      <span class="tool-status">{{ hasResult ? '已完成' : '执行中...' }}</span>
      <span class="tool-toggle">{{ expanded ? '▼' : '▶' }}</span>
    </div>
    <div v-if="expanded" class="tool-body">
      <div class="tool-section">
        <div class="tool-label">参数</div>
        <pre class="tool-code">{{ safeJson(args) }}</pre>
      </div>
      <div v-if="hasResult" class="tool-section">
        <div class="tool-label">结果</div>
        <pre class="tool-code">{{ safeJson(result) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, toRaw } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  args: { type: Object, default: () => ({}) },
  result: { type: [Object, String, Number, Array, null], default: null }
})

const expanded = ref(false)
const isWrite = computed(() => {
  const writeTools = ['create_trade', 'update_position', 'update_portfolio_config', 'sync_positions', 'dismiss_alert']
  return writeTools.includes(props.name)
})
const hasResult = computed(() => props.result !== null && props.result !== undefined)

function safeJson (val) {
  const raw = toRaw(val)
  if (raw === null || raw === undefined) return 'null'
  if (typeof raw !== 'object') return String(raw)
  try {
    return JSON.stringify(raw, null, 2)
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('AgentToolCall: 无法序列化 result:', raw, e)
    return '[无法序列化的对象]'
  }
}

const displayName = computed(() => {
  const map = {
    query_stock_basic: '查询股票基本信息',
    query_stock_daily: '查询日线数据',
    query_stock_indicator: '查询技术指标',
    query_financial_indicator: '查询财务指标',
    run_mainwave_picker: '主升浪选股',
    query_portfolio_positions: '查询持仓',
    query_portfolio_trades: '查询交易记录',
    query_portfolio_summary: '查询资产总览',
    query_portfolio_daily_pnl: '查询每日盈亏',
    query_portfolio_closed: '查询清仓记录',
    query_portfolio_alerts: '查询持仓预警',
    query_sync_job_logs: '查询同步日志',
    query_db_status: '查询数据库状态',
    query_market_sentiment: '查询市场情绪',
    create_trade: '录入交易',
    update_position: '更新持仓',
    update_portfolio_config: '更新配置',
    sync_positions: '同步持仓',
    dismiss_alert: '标记预警已处理'
  }
  return map[props.name] || props.name
})
</script>

<style lang="scss" scoped>
.tool-call-card {
  border: 1px solid var(--rule);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-secondary);

  &.tool-write {
    border-color: rgba(234, 179, 8, 0.4);
  }
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 12px;
  user-select: none;

  &:hover {
    background: var(--bg-hover);
  }

  .tool-icon {
    font-size: 13px;
  }

  .tool-name {
    font-weight: 500;
    color: var(--text-primary);
  }

  .tool-status {
    margin-left: auto;
    font-size: 11px;
    color: var(--text-faint);
  }

  .tool-toggle {
    font-size: 10px;
    color: var(--text-faint);
    width: 14px;
    text-align: center;
  }
}

.tool-body {
  padding: 0 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-section {
  .tool-label {
    font-size: 10px;
    color: var(--text-faint);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
}

.tool-code {
  background: var(--bg-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary);
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
