<script setup>
import { useViewport } from '@/composables/useViewport'
import MobileCardList from '@/components/common/MobileCardList.vue'

const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'roe' },
  sortOrder: { type: String, default: 'desc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const { isMobile } = useViewport()

const sortableColumns = [
  { key: 'roe', label: 'ROE' },
  { key: 'gross_profit_ratio', label: '毛利率' },
  { key: 'net_profit_ratio', label: '净利率' },
  { key: 'net_profit_yoy', label: '净利润同比' },
  { key: 'revenue_yoy', label: '营收同比' },
  { key: 'eps', label: 'EPS' },
  { key: 'debt_ratio', label: '资产负债率' }
]

const columns = [
  { key: 'symbol', label: '股票代码', align: 'left' },
  { key: 'name', label: '股票名称', align: 'left' },
  { key: 'industry', label: '所属行业', align: 'left' },
  { key: 'market', label: '市场板块', align: 'center' },
  { key: 'roe', label: 'ROE', align: 'right' },
  { key: 'gross_profit_ratio', label: '毛利率', align: 'right' },
  { key: 'net_profit_ratio', label: '净利率', align: 'right' },
  { key: 'net_profit_yoy', label: '净利润同比', align: 'right' },
  { key: 'revenue_yoy', label: '营收同比', align: 'right' },
  { key: 'eps', label: 'EPS', align: 'right' },
  { key: 'debt_ratio', label: '资产负债率', align: 'right' }
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

function formatPercent (val) {
  if (val == null || val === undefined) return '—'
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

function getYoyClass (val) {
  if (val == null) return ''
  return Number(val) >= 0 ? 'up' : 'down'
}

function onRowDblClick (item) {
  emit('row-dblclick', item)
}

function onRowClick (item) {
  emit('row-dblclick', item)
}
</script>

<template>
  <div class="table-section">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">暂无数据</div>
    <div v-else-if="isMobile" class="mobile-table">
      <div class="mobile-sort-bar">
        <span class="sort-label">排序</span>
        <button
          v-for="col in sortableColumns"
          :key="col.key"
          class="sort-btn"
          :class="{ active: sortField === col.key }"
          @click="onSort(col.key)"
        >
          {{ col.label }}
          <span v-if="sortField === col.key" class="sort-dir">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
        </button>
      </div>
      <MobileCardList
        :list="list"
        key-field="symbol"
        @click-item="onRowClick"
      >
        <template #default="{ item }">
          <div class="stock-card">
            <div class="card-header">
              <span class="card-code">{{ extractCodeNum(item.symbol) }}</span>
              <span class="card-name">{{ item.name }}</span>
              <span class="card-market">{{ item.market || '—' }}</span>
            </div>
            <div class="card-fields">
              <div class="card-field wide">
                <span class="field-label">所属行业</span>
                <span class="field-value">{{ item.industry || '—' }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">ROE</span>
                <span class="field-value">{{ item.roe != null ? `${item.roe.toFixed(2)}%` : '—' }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">毛利率</span>
                <span class="field-value">{{ item.gross_profit_ratio != null ? `${item.gross_profit_ratio.toFixed(2)}%` : '—' }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">净利率</span>
                <span class="field-value">{{ item.net_profit_ratio != null ? `${item.net_profit_ratio.toFixed(2)}%` : '—' }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">净利润同比</span>
                <span class="field-value" :class="getYoyClass(item.net_profit_yoy)">{{ formatPercent(item.net_profit_yoy) }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">营收同比</span>
                <span class="field-value" :class="getYoyClass(item.revenue_yoy)">{{ formatPercent(item.revenue_yoy) }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">EPS</span>
                <span class="field-value">{{ item.eps != null ? item.eps.toFixed(2) : '—' }}</span>
              </div>
              <div class="card-field">
                <span class="field-label">资产负债率</span>
                <span class="field-value">{{ item.debt_ratio != null ? `${item.debt_ratio.toFixed(2)}%` : '—' }}</span>
              </div>
            </div>
          </div>
        </template>
      </MobileCardList>
    </div>
    <table v-else class="stock-table">
      <colgroup>
        <col style="width: 8%">
        <col style="width: 10%">
        <col style="width: 12%">
        <col style="width: 8%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 8%">
        <col style="width: 8%">
        <col style="width: 6%">
        <col style="width: 9%">
      </colgroup>
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="sortable"
            :class="{ 'th-left': col.align === 'left', 'th-center': col.align === 'center' }"
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
          :key="item.symbol"
          class="data-row"
          @dblclick="onRowDblClick(item)"
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td class="td-left">{{ item.industry || '—' }}</td>
          <td class="td-center">{{ item.market || '—' }}</td>
          <td>{{ item.roe != null ? `${item.roe.toFixed(2)}%` : '—' }}</td>
          <td>{{ item.gross_profit_ratio != null ? `${item.gross_profit_ratio.toFixed(2)}%` : '—' }}</td>
          <td>{{ item.net_profit_ratio != null ? `${item.net_profit_ratio.toFixed(2)}%` : '—' }}</td>
          <td :class="getYoyClass(item.net_profit_yoy)">{{ formatPercent(item.net_profit_yoy) }}</td>
          <td :class="getYoyClass(item.revenue_yoy)">{{ formatPercent(item.revenue_yoy) }}</td>
          <td>{{ item.eps != null ? item.eps.toFixed(2) : '—' }}</td>
          <td>{{ item.debt_ratio != null ? `${item.debt_ratio.toFixed(2)}%` : '—' }}</td>
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
  width: 100%;
}

.mobile-sort-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  .sort-label {
    font-size: 11px;
    color: var(--text-faint);
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .sort-btn {
    flex-shrink: 0;
    padding: 6px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--rule);
    border-radius: 4px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    font-family: var(--font-body);

    &.active {
      border-color: var(--accent);
      color: var(--accent);
    }
  }

  .sort-dir {
    margin-left: 4px;
    font-size: 10px;
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

  .card-market {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
    padding: 2px 8px;
    border: 1px solid var(--rule);
    border-radius: 4px;
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

    &.wide {
      grid-column: 1 / -1;
    }
  }

  .field-label {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .field-value {
    font-size: 13px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
