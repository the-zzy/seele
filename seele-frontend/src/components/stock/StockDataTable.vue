<script setup>
import { useViewport } from '@/composables/useViewport'
import MobileCardList from '@/components/common/MobileCardList.vue'
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

const { isMobile } = useViewport()

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

function onClick (item) {
  emit('row-dblclick', item)
}

function getChgBgClass (val) {
  if (!val) return ''
  const value = parseFloat(val)
  if (value > 0) return 'up-bg'
  if (value < 0) return 'down-bg'
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
            <span class="card-date">{{ formatDate(item.tradeDate) }}</span>
          </div>
          <div class="card-fields">
            <div class="card-field">
              <span class="field-label">收盘</span>
              <span class="field-value" :class="getPriceClass(item.close, item.pctChg)">{{ formatNumber(item.close) }}</span>
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
              <span class="field-label">成交额</span>
              <span class="field-value">{{ formatAmount(item.amount) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">换手</span>
              <span class="field-value">{{ formatTurnover(item.turnover) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">振幅</span>
              <span class="field-value">{{ formatNumber(item.amplitude) }}%</span>
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
  overflow-x: auto;
}

.stock-table {
  min-width: 1100px;
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

  .card-date {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
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
