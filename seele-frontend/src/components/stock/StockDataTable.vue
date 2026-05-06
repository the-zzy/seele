<script setup>
import {
  formatDate,
  formatNumber,
  formatPctChg,
  formatVolume,
  formatAmount,
  formatTurnover,
  getPriceClass
} from '@/utils/formatters'

const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'symbol' },
  sortOrder: { type: String, default: 'asc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const columns = [
  { key: 'symbol', label: '代码', align: 'left' },
  { key: 'name', label: '名称', align: 'left' },
  { key: 'tradeDate', label: '交易日', align: 'center' },
  { key: 'open', label: '开盘' },
  { key: 'high', label: '最高' },
  { key: 'low', label: '最低' },
  { key: 'close', label: '收盘' },
  { key: 'priceChange', label: '涨跌额' },
  { key: 'pctChg', label: '涨跌幅' },
  { key: 'amplitude', label: '振幅' },
  { key: 'volume', label: '成交量' },
  { key: 'amount', label: '成交额' },
  { key: 'turnover', label: '换手' }
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

function getChgBgClass (val) {
  if (!val) return ''
  const value = parseFloat(val)
  if (value > 0) return 'up-bg'
  if (value < 0) return 'down-bg'
  return ''
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
          @dblclick="onDblClick(item)"
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td class="td-center">{{ formatDate(item.tradeDate) }}</td>
          <td :class="getPriceClass(item.open, item.pctChg)">{{ formatNumber(item.open) }}</td>
          <td :class="getPriceClass(item.high, item.pctChg)">{{ formatNumber(item.high) }}</td>
          <td :class="getPriceClass(item.low, item.pctChg)">{{ formatNumber(item.low) }}</td>
          <td :class="getPriceClass(item.close, item.pctChg)">{{ formatNumber(item.close) }}</td>
          <td :class="getChgBgClass(item.priceChange)">
            {{ item.priceChange > 0 ? '+' : '' }}{{ formatNumber(item.priceChange) }}
          </td>
          <td :class="getChgBgClass(item.pctChg)">{{ formatPctChg(item.pctChg) }}</td>
          <td>{{ formatNumber(item.amplitude) }}%</td>
          <td>{{ formatVolume(item.volume) }}</td>
          <td>{{ formatAmount(item.amount) }}</td>
          <td>{{ formatTurnover(item.turnover) }}</td>
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
  font-family: var(--font-mono);
  font-size: 14px;
  font-variant-numeric: tabular-nums;

  th,
  td {
    padding: 11px 14px;
    text-align: right;
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
    border-bottom: 1px solid var(--rule);

    .th-label { display: inline-block; }

    &.sortable {
      cursor: pointer;
      user-select: none;
      transition: color 0.15s;

      &:hover {
        color: var(--text-secondary);
      }

      .sort-icon {
        margin-left: 6px;
        font-size: 11px;
        opacity: 0.5;
      }
    }
  }

  tbody tr {
    cursor: pointer;
    transition: background 0.12s;

    &:hover {
      background: var(--bg-tertiary);
    }
  }

  td {
    color: var(--text-primary);

    &.td-center { text-align: center; }
  }

  .code {
    text-align: left;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: 0.04em;
  }

  .name {
    text-align: left;
    font-family: var(--font-body);
    font-weight: 500;
    color: var(--text-primary);
  }

  .up { color: var(--up); }
  .down { color: var(--down); }

  .up-bg {
    color: var(--up);
    box-shadow: inset 2px 0 0 var(--up);
  }

  .down-bg {
    color: var(--down);
    box-shadow: inset 2px 0 0 var(--down);
  }
}
</style>
