<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockDailyApi } from '@/api/stock'
import { useStockPicker } from '@/composables/useStockPicker'
import { getLatestTradeDate } from '@/utils/date'
import { formatNumber, formatPctChg, formatAmount, formatTurnover, getPctChgClass } from '@/utils/formatters'
import BasePagination from '@/components/common/BasePagination.vue'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const filters = ref({
  trade_date: '',
  only_s_level: false,
  exclude_st: true,
  exclude_cyb: true,
  exclude_kcb: true,
  exclude_bse: true,
  sort_field: 'level',
  sort_order: 'desc'
})

const {
  loading,
  total,
  pageNum,
  pageSize,
  sortField,
  sortOrder,
  displayList,
  search,
  handleSort,
  handlePageChange,
  handlePageSizeChange
} = useStockPicker({
  fetcher: (params) => stockDailyApi.getMainwavePicker(params).then(res => res.data),
  defaultSortField: 'level',
  defaultSortOrder: 'desc',
  serverSort: true,
  defaultPageSize: 20
})

onMounted(async () => {
  const latestDate = await getLatestTradeDate()
  filters.value.trade_date = latestDate
  handleSearch()
})

function handleSearch () {
  const params = { ...filters.value }
  if (!params.trade_date) {
    delete params.trade_date
  }
  search(params)
}

function handleRowDblClick (item) {
  if (!item.symbol) return
  router.push({
    name: 'stock-kline',
    params: { symbol: item.symbol },
    query: { name: item.name || '' }
  })
}

function getSortIcon (field) {
  if (sortField.value !== field) return '⇅'
  return sortOrder.value === 'asc' ? '▲' : '▼'
}

function getLevelClass (level) {
  if (level === 'S') return 'level-s'
  return 'level-gamble'
}
</script>

<template>
  <div class="picker-page">
    <PageHero
      section="选股策略"
      number="03.7"
      title="主升浪选股"
      description="基于5条硬性门槛 + 3条主升浪判定标准 + 级别评分的选股策略。"
      meta="技术面"
    />

    <div class="filter-panel">
      <div class="filter-row">
        <div class="filter-item">
          <label>交易日期</label>
          <input v-model="filters.trade_date" type="date" />
        </div>
        <div class="filter-item checkbox">
          <label><input v-model="filters.only_s_level" type="checkbox" /> 仅看硬核S级</label>
        </div>
        <div class="filter-item checkbox">
          <label><input v-model="filters.exclude_st" type="checkbox" /> 排除ST</label>
        </div>
        <div class="filter-item checkbox">
          <label><input v-model="filters.exclude_cyb" type="checkbox" /> 排除创业板</label>
        </div>
        <div class="filter-item checkbox">
          <label><input v-model="filters.exclude_kcb" type="checkbox" /> 排除科创板</label>
        </div>
        <div class="filter-item checkbox">
          <label><input v-model="filters.exclude_bse" type="checkbox" /> 排除北交所</label>
        </div>
      </div>
      <div class="filter-actions">
        <button class="btn-primary" @click="handleSearch">筛选</button>
      </div>
    </div>

    <div class="result-bar">共 {{ total }} 只</div>

    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th>股票</th>
            <th>级别</th>
            <th @click="handleSort('pct_chg')">收盘价 / 涨幅 {{ getSortIcon('pct_chg') }}</th>
            <th>MA5</th>
            <th>MA10</th>
            <th>流通市值</th>
            <th>10日换手</th>
            <th>10日成交额</th>
            <th>净利润同比</th>
            <th>信号</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in displayList" :key="item.symbol" @dblclick="handleRowDblClick(item)">
            <td>
              <div class="stock-name">
                <span class="symbol">{{ item.symbol }}</span>
                <span class="name">{{ item.name }}</span>
                <span v-if="item.industry" class="industry">{{ item.industry }}</span>
              </div>
            </td>
            <td>
              <span class="level-tag" :class="getLevelClass(item.level)">
                {{ item.level === 'S' ? '硬核S级' : '博弈级' }}
              </span>
            </td>
            <td>
              <div class="price-col">
                <span>{{ formatNumber(item.close) }}</span>
                <span :class="getPctChgClass(item.pct_chg)">{{ formatPctChg(item.pct_chg) }}</span>
              </div>
            </td>
            <td>{{ formatNumber(item.ma5) }}</td>
            <td>{{ formatNumber(item.ma10) }}</td>
            <td>{{ item.float_market_cap ? item.float_market_cap.toFixed(2) + '亿' : '-' }}</td>
            <td>{{ formatTurnover(item.turnover_ma10) }}</td>
            <td>{{ formatAmount(item.amount_ma10) }}</td>
            <td :class="{ 'up': item.net_profit_yoy > 0, 'down': item.net_profit_yoy < 0 }">
              {{ item.net_profit_yoy !== null ? item.net_profit_yoy.toFixed(2) + '%' : '-' }}
            </td>
            <td class="signals">{{ item.signals }}</td>
          </tr>
          <tr v-if="!loading && displayList.length === 0">
            <td colspan="10" class="empty">暂无数据，请调整筛选条件</td>
          </tr>
        </tbody>
      </table>
      <div v-if="loading" class="loading-mask">加载中...</div>
    </div>

    <BasePagination
      v-if="total > 0"
      :page-num="pageNum"
      :page-size="pageSize"
      :total="total"
      @update:page-num="handlePageChange"
      @update:page-size="handlePageSizeChange"
    />
  </div>
</template>

<style scoped lang="scss">
@import '~@/styles/picker';

.level-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;

  &.level-s {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
  }

  &.level-gamble {
    background: rgba(234, 179, 8, 0.15);
    color: #eab308;
    border: 1px solid rgba(234, 179, 8, 0.3);
  }
}

.price-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-end;

  span:first-child {
    color: var(--text-primary);
  }
}

.signals {
  font-size: 11px;
  color: var(--text-secondary);
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
