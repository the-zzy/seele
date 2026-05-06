<script setup>
import {
  formatNumber,
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
          <th>行业</th>
          <th>收盘价</th>
          <th class="sortable" @click="handleSort('pct_chg')">
            涨跌幅<span class="sort-icon">{{ getSortIcon('pct_chg') }}</span>
          </th>
          <th class="sortable" @click="handleSort('amount')">
            成交额<span class="sort-icon">{{ getSortIcon('amount') }}</span>
          </th>
          <th class="sortable" @click="handleSort('turnover')">
            换手率<span class="sort-icon">{{ getSortIcon('turnover') }}</span>
          </th>
          <th class="sortable" @click="handleSort('ma5')">
            MA5<span class="sort-icon">{{ getSortIcon('ma5') }}</span>
          </th>
          <th class="sortable" @click="handleSort('ma10')">
            MA10<span class="sort-icon">{{ getSortIcon('ma10') }}</span>
          </th>
          <th class="sortable" @click="handleSort('ma20')">
            MA20<span class="sort-icon">{{ getSortIcon('ma20') }}</span>
          </th>
          <th class="sortable" @click="handleSort('ma60')">
            MA60<span class="sort-icon">{{ getSortIcon('ma60') }}</span>
          </th>
          <th>MACD DIF</th>
          <th>MACD DEA</th>
          <th class="sortable" @click="handleSort('rsi_14')">
            RSI(14)<span class="sort-icon">{{ getSortIcon('rsi_14') }}</span>
          </th>
          <th class="sortable" @click="handleSort('volume_ratio')">
            量比<span class="sort-icon">{{ getSortIcon('volume_ratio') }}</span>
          </th>
          <th class="sortable" @click="handleSort('score')">
            评分<span class="sort-icon">{{ getSortIcon('score') }}</span>
          </th>
          <th>信号</th>
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
          <td class="name">{{ item.name || '-' }}</td>
          <td>{{ item.industry || '-' }}</td>
          <td>{{ formatNumber(item.close) }}</td>
          <td :class="['chg-cell', getPctChgClass(item.pct_chg) + '-bg']">
            {{ formatPctChg(item.pct_chg) }}
          </td>
          <td>{{ formatAmount(item.amount) }}</td>
          <td>{{ formatTurnover(item.turnover) }}</td>
          <td>{{ item.ma5 != null ? formatNumber(item.ma5) : '-' }}</td>
          <td>{{ item.ma10 != null ? formatNumber(item.ma10) : '-' }}</td>
          <td>{{ item.ma20 != null ? formatNumber(item.ma20) : '-' }}</td>
          <td>{{ item.ma60 != null ? formatNumber(item.ma60) : '-' }}</td>
          <td>{{ item.macd_dif != null ? formatNumber(item.macd_dif, 4) : '-' }}</td>
          <td>{{ item.macd_dea != null ? formatNumber(item.macd_dea, 4) : '-' }}</td>
          <td>{{ item.rsi_14 != null ? formatNumber(item.rsi_14) : '-' }}</td>
          <td>{{ item.volume_ratio != null ? formatNumber(item.volume_ratio) : '-' }}</td>
          <td class="highlight">{{ item.trend_score != null ? item.trend_score : '-' }}</td>
          <td>{{ item.signals || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';
</style>
