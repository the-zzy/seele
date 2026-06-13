<script setup>
import { useViewport } from '@/composables/useViewport'
import MobileCardList from '@/components/common/MobileCardList.vue'
import {
  formatNumber,
  formatPctChg,
  formatVolume,
  formatTurnover
} from '@/utils/formatters'

const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'symbol' },
  sortOrder: { type: String, default: 'asc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const { isMobile } = useViewport()

const columns = [
  { key: 'symbol', label: '代码', align: 'left' },
  { key: 'name', label: '名称', align: 'left' },
  { key: 'score', label: '总分' },
  { key: 'close', label: '收盘' },
  { key: 'pctChg', label: '涨跌幅' },
  { key: 'volume', label: '成交量' },
  { key: 'turnover', label: '换手' },
  { key: 'ma5', label: 'MA5' },
  { key: 'deviateMa5', label: '偏离MA5' },
  { key: 'chg5d', label: '5日涨幅' },
  { key: 'chg10d', label: '10日涨幅' },
  { key: 'netProfitYoy', label: '净利润同比' },
  { key: 'roe', label: 'ROE' }
]

function getDeviateMa5 (item) {
  const close = parseFloat(item.close)
  const ma5 = parseFloat(item.ma5)
  if (!close || !ma5 || ma5 === 0) return '-'
  return ((close - ma5) / ma5 * 100).toFixed(2)
}

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

function onDblClick (item) {
  emit('row-dblclick', item)
}

function onClick (item) {
  emit('row-dblclick', item)
}

function getScoreClass (score) {
  if (!score || score.total === undefined) return ''
  const total = score.total
  if (total >= 80) return 'score-strong'
  if (total >= 60) return 'score-ok'
  if (total >= 40) return 'score-weak'
  return 'score-poor'
}

function getScoreLabel (score) {
  if (!score || score.total === undefined) return '—'
  const total = score.total
  if (total >= 80) return `${total} 强推`
  if (total >= 60) return `${total} 推荐`
  if (total >= 40) return `${total} 勉强`
  return `${total} 不推荐`
}

function getScoreTooltip (item) {
  const s = item.score
  if (!s) return ''
  return [
    `总分: ${s.total}`,
    `趋势分: ${s.trend_score}`,
    `强势分: ${s.strength_score}`,
    `动量分: ${s.momentum_score}`,
    s.hard_pass ? '硬性门槛: 通过' : '硬性门槛: 未通过'
  ].join('\n')
}

function getChgBgClass (val) {
  if (val === null || val === undefined) return ''
  const value = parseFloat(val)
  if (value > 0) return 'up-bg'
  if (value < 0) return 'down-bg'
  return ''
}

function getPriceClass (pctChg) {
  if (pctChg === null || pctChg === undefined) return ''
  const value = parseFloat(pctChg)
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return ''
}

function getChgClass (val) {
  if (val == null) return ''
  const value = parseFloat(val)
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return ''
}
</script>

<template>
  <div class="table-section">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">暂无数据</div>
    <MobileCardList
      v-else-if="isMobile"
      :list="list"
      key-field="id"
      @click-item="onClick"
    >
      <template #default="{ item }">
        <div class="stock-card">
          <div class="card-header">
            <span class="card-code">{{ extractCodeNum(item.symbol) }}</span>
            <span class="card-name">{{ item.name }}</span>
            <span
              class="score-tag"
              :class="getScoreClass(item.score)"
              :title="getScoreTooltip(item)"
            >{{ getScoreLabel(item.score) }}</span>
          </div>
          <div class="card-fields">
            <div class="card-field">
              <span class="field-label">收盘</span>
              <span class="field-value" :class="getPriceClass(item.pctChg)">{{ formatNumber(item.close) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">涨跌幅</span>
              <span class="field-value" :class="getChgClass(item.pctChg)">{{ formatPctChg(item.pctChg) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">成交量</span>
              <span class="field-value">{{ formatVolume(item.volume) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">换手</span>
              <span class="field-value">{{ formatTurnover(item.turnover) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">5日涨幅</span>
              <span class="field-value" :class="getChgClass(item.chg5d)">{{ item.chg5d > 0 ? '+' : '' }}{{ formatNumber(item.chg5d) }}%</span>
            </div>
            <div class="card-field">
              <span class="field-label">10日涨幅</span>
              <span class="field-value" :class="getChgClass(item.chg10d)">{{ item.chg10d > 0 ? '+' : '' }}{{ formatNumber(item.chg10d) }}%</span>
            </div>
            <div class="card-field">
              <span class="field-label">净利润同比</span>
              <span class="field-value" :class="getChgClass(item.netProfitYoy)">{{ item.netProfitYoy != null ? (item.netProfitYoy > 0 ? '+' : '') + formatNumber(item.netProfitYoy) + '%' : '-' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">ROE</span>
              <span class="field-value">{{ item.roe != null ? formatNumber(item.roe) + '%' : '-' }}</span>
            </div>
          </div>
        </div>
      </template>
    </MobileCardList>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="sortable"
            :style="{ textAlign: col.align || 'right' }"
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
          :key="item.id"
          class="data-row"
          @dblclick="onDblClick(item)"
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td :title="getScoreTooltip(item)">
            <span class="score-tag" :class="getScoreClass(item.score)">
              {{ getScoreLabel(item.score) }}
            </span>
          </td>
          <td :class="getPriceClass(item.pctChg)">{{ formatNumber(item.close) }}</td>
          <td :class="getChgBgClass(item.pctChg)">{{ formatPctChg(item.pctChg) }}</td>
          <td>{{ formatVolume(item.volume) }}</td>
          <td>{{ formatTurnover(item.turnover) }}</td>
          <td>{{ formatNumber(item.ma5) }}</td>
          <td :class="getChgBgClass(getDeviateMa5(item))">{{ getDeviateMa5(item) > 0 ? '+' : '' }}{{ getDeviateMa5(item) }}%</td>
          <td :class="getChgBgClass(item.chg5d)">{{ item.chg5d > 0 ? '+' : '' }}{{ formatNumber(item.chg5d) }}%</td>
          <td :class="getChgBgClass(item.chg10d)">{{ item.chg10d > 0 ? '+' : '' }}{{ formatNumber(item.chg10d) }}%</td>
          <td :class="getChgBgClass(item.netProfitYoy)">{{ item.netProfitYoy != null ? (item.netProfitYoy > 0 ? '+' : '') + formatNumber(item.netProfitYoy) + '%' : '-' }}</td>
          <td>{{ item.roe != null ? formatNumber(item.roe) + '%' : '-' }}</td>
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
  min-width: 1400px;
}

.score-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: help;

  &.score-strong {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
  }

  &.score-ok {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  &.score-weak {
    background: rgba(156, 163, 175, 0.15);
    color: #9ca3af;
    border: 1px solid rgba(156, 163, 175, 0.3);
  }

  &.score-poor {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }
}

.stock-card {
  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--rule);
  }

  .card-code {
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .card-name {
    flex: 1;
    font-family: var(--font-body);
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-fields {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px 16px;
  }

  .card-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .field-label {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .field-value {
    font-size: 13px;
    color: var(--text-primary);
  }
}
</style>
