<script setup>
import { useViewport } from '@/composables/useViewport'
import { useFixedRows } from '@/composables/useFixedRows'
import MobileCardList from '@/components/common/MobileCardList.vue'
import { formatNumber } from '@/utils/formatters'

const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'score' },
  sortOrder: { type: String, default: 'desc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const { isMobile } = useViewport()

const paddedList = useFixedRows(() => props.list)

const columns = [
  { key: 'symbol', label: '代码', align: 'left' },
  { key: 'name', label: '名称', align: 'left' },
  { key: 'score', label: '总分', align: 'center' },
  { key: 'trendScore', label: '趋势分', align: 'center' },
  { key: 'strengthScore', label: '强势分', align: 'center' },
  { key: 'momentumScore', label: '动量分', align: 'center' },
  { key: 'hardPass', label: '硬性门槛', align: 'center' }
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
  return [
    `总分: ${s.total}`,
    `趋势分: ${s.trend_score}`,
    `强势分: ${s.strength_score}`,
    `动量分: ${s.momentum_score}`,
    s.hard_pass ? '硬性门槛: 通过' : '硬性门槛: 未通过'
  ].join('\n')
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
        <div
          class="stock-card"
          :class="{ 'hard-fail': item.score && !item.score.hard_pass, holding: item.isHolding }"
        >
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
              <span class="field-label">趋势分</span>
              <span class="field-value">{{ item.score?.trend_score ?? '—' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">强势分</span>
              <span class="field-value">{{ item.score?.strength_score ?? '—' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">动量分</span>
              <span class="field-value">{{ item.score?.momentum_score ?? '—' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">硬性门槛</span>
              <span class="field-value" :class="getHardPassClass(item.score)">{{ getHardPassLabel(item.score) }}</span>
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
          v-for="(item, index) in paddedList"
          :key="item === null ? `empty-${index}` : (item.id || item.symbol || index)"
          class="data-row"
          :class="{ 'hard-fail': item && item.score && !item.score.hard_pass, holding: item && item.isHolding, 'empty-row': item === null }"
          @dblclick="item && onDblClick(item)"
        >
          <template v-if="item">
            <td class="code">{{ extractCodeNum(item.symbol) }}</td>
            <td class="name">{{ item.name }}</td>
            <td :class="getScoreClass(item.score)" :title="getScoreTooltip(item)">
              {{ getScoreLabel(item.score) }}
            </td>
            <td>{{ item.score?.trend_score ?? '—' }}</td>
            <td>{{ item.score?.strength_score ?? '—' }}</td>
            <td>{{ item.score?.momentum_score ?? '—' }}</td>
            <td :class="getHardPassClass(item.score)">{{ getHardPassLabel(item.score) }}</td>
          </template>
          <template v-else>
            <td v-for="col in columns" :key="col.key">&nbsp;</td>
          </template>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.table-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.stock-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 800px;

  thead,
  tbody {
    display: flex;
    flex-direction: column;
  }

  thead {
    flex-shrink: 0;
  }

  tbody {
    flex: 1;
    overflow-y: auto;
  }

  tr {
    display: flex;
    flex: 0 0 10%;
    min-height: 0;
  }

  th,
  td {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  th:first-child,
  td:first-child,
  th:nth-child(2),
  td:nth-child(2) {
    justify-content: flex-start;
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

.stock-card {
  &.hard-fail {
    opacity: 0.65;
  }

  &.holding {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.2);
  }

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
