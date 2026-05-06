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
          <th class="sortable" @click="handleSort('close')">
            收盘价<span class="sort-icon">{{ getSortIcon('close') }}</span>
          </th>
          <th class="sortable" @click="handleSort('pct_chg')">
            涨跌幅<span class="sort-icon">{{ getSortIcon('pct_chg') }}</span>
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
          <th class="sortable" @click="handleSort('ma250')">
            MA250<span class="sort-icon">{{ getSortIcon('ma250') }}</span>
          </th>
          <th class="sortable" @click="handleSort('high_60')">
            60日高点<span class="sort-icon">{{ getSortIcon('high_60') }}</span>
          </th>
          <th>站上年线</th>
          <th>突破平台</th>
          <th>倍量</th>
          <th class="sortable" @click="handleSort('avg_volume_20')">
            20日均量<span class="sort-icon">{{ getSortIcon('avg_volume_20') }}</span>
          </th>
          <th class="sortable" @click="handleSort('current_return')">
            当前收益<span class="sort-icon">{{ getSortIcon('current_return') }}</span>
          </th>
          <th class="sortable" @click="handleSort('max_return')">
            最大收益<span class="sort-icon">{{ getSortIcon('max_return') }}</span>
          </th>
          <th class="sortable" @click="handleSort('latest_date')">
            最新日期<span class="sort-icon">{{ getSortIcon('latest_date') }}</span>
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
          <td class="name">{{ item.name }}</td>
          <td>{{ formatNumber(item.close) }}</td>
          <td :class="['chg-cell', getPctChgClass(item.pct_chg) + '-bg']">
            {{ formatPctChg(item.pct_chg) }}
          </td>
          <td>{{ formatVolume(item.volume) }}</td>
          <td>{{ formatAmount(item.amount) }}</td>
          <td>{{ formatTurnover(item.turnover) }}</td>
          <td>{{ item.ma250 ? formatNumber(item.ma250) : '-' }}</td>
          <td>{{ item.high_60 ? formatNumber(item.high_60) : '-' }}</td>
          <td>
            <span :class="['tag', item.above_ma250 ? 'tag-ok' : 'tag-no']">
              {{ item.above_ma250 ? '是' : '否' }}
            </span>
          </td>
          <td>
            <span :class="['tag', item.is_breakout ? 'tag-ok' : 'tag-no']">
              {{ item.is_breakout ? '是' : '否' }}
            </span>
          </td>
          <td>
            <span :class="['tag', item.is_double_volume ? 'tag-ok' : 'tag-no']">
              {{ item.is_double_volume ? '是' : '否' }}
            </span>
          </td>
          <td>{{ item.avg_volume_20 ? formatVolume(item.avg_volume_20) : '-' }}</td>
          <td :class="['chg-cell', getPctChgClass(item.current_return) + '-bg']">
            {{ item.current_return != null ? formatPctChg(item.current_return) : '-' }}
          </td>
          <td :class="['chg-cell', getPctChgClass(item.max_return) + '-bg']">
            {{ item.max_return != null ? formatPctChg(item.max_return) : '-' }}
          </td>
          <td>{{ item.latest_date || '-' }}</td>
          <td>{{ item.signals || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';
</style>
