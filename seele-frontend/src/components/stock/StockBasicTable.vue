<script setup>
const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'symbol' },
  sortOrder: { type: String, default: 'asc' },
  loading: Boolean
})

const emit = defineEmits(['sort'])

const columns = [
  { key: 'symbol', label: '股票代码', align: 'left' },
  { key: 'name', label: '股票名称', align: 'left' },
  { key: 'industry', label: '所属行业', align: 'left' },
  { key: 'area', label: '所在地区', align: 'left' },
  { key: 'market', label: '市场板块', align: 'center' },
  { key: 'listDate', label: '上市日期', align: 'center' }
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

function formatDate (val) {
  if (!val) return '-'
  const s = String(val)
  if (s.length === 8) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  }
  return s
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
            :style="{ textAlign: col.align || 'left' }"
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
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td>{{ item.industry || '—' }}</td>
          <td>{{ item.area || '—' }}</td>
          <td class="td-center market">{{ item.market || '—' }}</td>
          <td class="td-center">{{ formatDate(item.listDate) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.table-section {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  margin-top: 12px;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    border-radius: 4px;
    box-shadow: var(--shadow-soft);
  }
}

.state {
  text-align: center;
  padding: 60px 20px;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-faint);
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-body);
  font-size: 14px;

  th,
  td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
  }

  th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--bg-primary);
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);

    &.sortable {
      cursor: pointer;
      user-select: none;
      transition: color 0.15s;

      &:hover { color: var(--text-secondary); }

      .sort-icon {
        margin-left: 6px;
        font-size: 11px;
        opacity: 0.5;
      }
    }
  }

  tbody tr {
    transition: background 0.12s;

    &:hover { background: var(--bg-tertiary); }
  }

  td {
    color: var(--text-secondary);

    &.td-center { text-align: center; }
  }

  .code {
    font-family: var(--font-mono);
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: 0.04em;
  }

  .name {
    font-family: var(--font-display);
    font-weight: 500;
    font-size: 16px;
    color: var(--text-primary);
  }

  .market {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-faint);
  }
}
</style>
