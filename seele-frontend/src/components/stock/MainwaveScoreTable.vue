<script setup>
import { formatNumber } from '@/utils/formatters'

const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'score' },
  sortOrder: { type: String, default: 'desc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const columns = [
  { key: 'symbol', label: '代码', align: 'left' },
  { key: 'name', label: '名称', align: 'left' },
  { key: 'score', label: '总分', align: 'center' },
  { key: 'hardPass', label: '硬性门槛', align: 'center' },
  { key: 'deviateMa5', label: '偏离MA5', align: 'center' },
  { key: 'pullback', label: '距高点回落', align: 'center' },
  { key: 'kRatio', label: 'K线涨跌比', align: 'center' },
  { key: 'bigDrop', label: '大阴线', align: 'center' },
  { key: 'upperShadow', label: '上影线', align: 'center' },
  { key: 'direction', label: '方向分散', align: 'center' },
  { key: 'sector', label: '板块强度', align: 'center' },
  { key: 'earnings', label: '业绩质量', align: 'center' },
  { key: 'liquidity', label: '市值流动', align: 'center' },
  { key: 'catalyst', label: '催化剂', align: 'center' }
]

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

function getHardPassLabel (score) {
  if (!score) return '—'
  return score.hard_pass ? '通过' : '未通过'
}

function getHardPassClass (score) {
  if (!score) return ''
  return score.hard_pass ? 'pass' : 'fail'
}

function getScoreTooltip (item) {
  const s = item.score
  if (!s) return ''
  const trend = s.deviate_ma5 + s.pullback + s.k_ratio + s.big_drop + s.upper_shadow
  return [
    `总分: ${s.total}`,
    `趋势形态: ${trend}/30`,
    `  偏离MA5: ${s.deviate_ma5}`,
    `  距高点回落: ${s.pullback}`,
    `  K线涨跌比: ${s.k_ratio}`,
    `  大阴线: ${s.big_drop}`,
    `  上影线: ${s.upper_shadow}`,
    `方向分散: ${s.direction}/20`,
    `板块强度: ${s.sector}/20`,
    `业绩质量: ${s.earnings}/15`,
    `市值流动性: ${s.liquidity}/10`,
    `催化剂: ${s.catalyst}/5`,
    s.hard_pass ? '硬性门槛: 通过' : '硬性门槛: 未通过'
  ].join('\n')
}
</script>

<template>
  <div class="table-section">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">暂无数据</div>
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
          :class="{ 'hard-fail': item.score && !item.score.hard_pass, 'holding': item.isHolding }"
          @dblclick="onDblClick(item)"
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td :class="getScoreClass(item.score)" :title="getScoreTooltip(item)">
            {{ getScoreLabel(item.score) }}
          </td>
          <td :class="getHardPassClass(item.score)">{{ getHardPassLabel(item.score) }}</td>
          <td>{{ item.score?.deviate_ma5 ?? '—' }}</td>
          <td>{{ item.score?.pullback ?? '—' }}</td>
          <td>{{ item.score?.k_ratio ?? '—' }}</td>
          <td>{{ item.score?.big_drop ?? '—' }}</td>
          <td>{{ item.score?.upper_shadow ?? '—' }}</td>
          <td>{{ item.score?.direction ?? '—' }}</td>
          <td>{{ item.score?.sector ?? '—' }}</td>
          <td>{{ item.score?.earnings ?? '—' }}</td>
          <td>{{ item.score?.liquidity ?? '—' }}</td>
          <td>{{ item.score?.catalyst ?? '—' }}</td>
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

  .code {
    font-family: var(--font-mono);
    color: var(--text-secondary);
  }

  .name {
    font-weight: 500;
  }

  .data-row {
    &.hard-fail {
      opacity: 0.55;
    }

    &.holding {
      background: rgba(245, 158, 11, 0.08);
    }
  }
}

.score-strong {
  color: #22c55e;
  font-weight: 600;
}

.score-ok {
  color: #f59e0b;
  font-weight: 600;
}

.score-weak {
  color: #9ca3af;
}

.score-poor {
  color: #ef4444;
}

.pass {
  color: #22c55e;
}

.fail {
  color: #ef4444;
  font-weight: 600;
}
</style>
