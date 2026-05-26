<script setup>
import {
  formatDate,
  formatNumber,
  formatPctChg,
  formatVolume,
  formatAmount,
  formatTurnover
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
</style>
