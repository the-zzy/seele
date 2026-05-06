<script setup>
import {
  formatNumber,
  formatVolume,
  formatAmount,
  formatPctChg,
  formatTurnover,
  getPctChgClass
} from '@/utils/formatters'

const props = defineProps({
  items: { type: Array, required: true },
  sortField: { type: String, default: '' },
  sortOrder: { type: String, default: 'desc' },
  loading: { type: Boolean, default: false },
  total: { type: Number, default: 0 }
})

const emit = defineEmits(['sort', 'row-dblclick'])

function getSortIcon (field) {
  if (props.sortField !== field) return '⇅'
  return props.sortOrder === 'asc' ? '▲' : '▼'
}

function handleSort (field) {
  emit('sort', field)
}

function handleRowDblClick (item) {
  emit('row-dblclick', item)
}
</script>

<template>
  <div class="table-section">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="total === 0" class="empty">暂无数据</div>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th class="sortable" @click="handleSort('symbol')">
            股票代码<span class="sort-icon">{{ getSortIcon('symbol') }}</span>
          </th>
          <th class="sortable" @click="handleSort('name')">
            股票名称<span class="sort-icon">{{ getSortIcon('name') }}</span>
          </th>
          <th class="sortable" @click="handleSort('trade_date')">
            交易日<span class="sort-icon">{{ getSortIcon('trade_date') }}</span>
          </th>
          <th class="sortable" @click="handleSort('open')">
            开盘价<span class="sort-icon">{{ getSortIcon('open') }}</span>
          </th>
          <th class="sortable" @click="handleSort('high')">
            最高价<span class="sort-icon">{{ getSortIcon('high') }}</span>
          </th>
          <th class="sortable" @click="handleSort('low')">
            最低价<span class="sort-icon">{{ getSortIcon('low') }}</span>
          </th>
          <th class="sortable" @click="handleSort('close')">
            收盘价<span class="sort-icon">{{ getSortIcon('close') }}</span>
          </th>
          <th class="sortable" @click="handleSort('price_change')">
            涨跌额<span class="sort-icon">{{ getSortIcon('price_change') }}</span>
          </th>
          <th class="sortable" @click="handleSort('pct_chg')">
            涨跌幅<span class="sort-icon">{{ getSortIcon('pct_chg') }}</span>
          </th>
          <th class="sortable" @click="handleSort('amplitude')">
            振幅<span class="sort-icon">{{ getSortIcon('amplitude') }}</span>
          </th>
          <th class="sortable" @click="handleSort('volume')">
            成交量<span class="sort-icon">{{ getSortIcon('volume') }}</span>
          </th>
          <th class="sortable" @click="handleSort('amount')">
            成交额<span class="sort-icon">{{ getSortIcon('amount') }}</span>
          </th>
          <th class="sortable" @click="handleSort('turnover')">
            换手率<span class="sort-icon">{{ getSortIcon('turnover') }}</span>
          </th>
          <th class="sortable" @click="handleSort('consecutive_days')">
            连续缩量天数<span class="sort-icon">{{ getSortIcon('consecutive_days') }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in items"
          :key="item.symbol"
          class="data-row"
          @dblclick="handleRowDblClick(item)"
        >
          <td class="code">{{ item.symbol }}</td>
          <td class="name">{{ item.name || item.stock_name || '-' }}</td>
          <td>{{ item.trade_date || '-' }}</td>
          <td>{{ formatNumber(item.open) }}</td>
          <td>{{ formatNumber(item.high) }}</td>
          <td>{{ formatNumber(item.low) }}</td>
          <td>{{ formatNumber(item.close) }}</td>
          <td :class="['chg-cell', getPctChgClass(item.price_change) + '-bg']">
            {{ item.price_change > 0 ? '+' : '' }}{{ formatNumber(item.price_change) }}
          </td>
          <td :class="['chg-cell', getPctChgClass(item.pct_chg) + '-bg']">
            {{ formatPctChg(item.pct_chg) }}
          </td>
          <td>{{ item.amplitude != null ? formatNumber(item.amplitude) + '%' : '-' }}</td>
          <td>{{ formatVolume(item.volume) }}</td>
          <td>{{ formatAmount(item.amount) }}</td>
          <td>{{ formatTurnover(item.turnover) }}</td>
          <td class="highlight">{{ item.consecutive_days != null ? item.consecutive_days : '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';
</style>
