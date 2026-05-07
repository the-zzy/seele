<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { financialApi } from '@/api/financial'
import { useStockPicker } from '@/composables/useStockPicker'
import BasePagination from '@/components/common/BasePagination.vue'
import PageHero from '@/components/common/PageHero.vue'

const router = useRouter()

const filters = ref({
  roe_min: 15,
  gross_profit_ratio_min: 30,
  net_profit_ratio_min: null,
  net_profit_yoy_min: 20,
  revenue_yoy_min: 15,
  debt_ratio_max: 60,
  exclude_st: true,
  exclude_cyb: true,
  exclude_kcb: true,
  exclude_bse: true,
  sort_field: 'roe',
  sort_order: 'desc'
})

const syncLoading = ref(false)
const syncMessage = ref('')

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
  fetcher: (params) => financialApi.picker(params).then(res => res.data),
  defaultSortField: 'roe',
  defaultSortOrder: 'desc',
  serverSort: true,
  defaultPageSize: 20
})

function handleSearch () {
  const params = { ...filters.value }
  // 移除 null 值
  Object.keys(params).forEach(key => {
    if (params[key] === null || params[key] === '') {
      delete params[key]
    }
  })
  search(params)
}

function handleSync () {
  syncLoading.value = true
  syncMessage.value = '同步中...'
  financialApi.syncAll()
    .then(res => {
      syncMessage.value = res.data?.hint || '同步任务已提交'
    })
    .catch(err => {
      syncMessage.value = '同步失败: ' + (err.message || '未知错误')
    })
    .finally(() => {
      syncLoading.value = false
      setTimeout(() => { syncMessage.value = '' }, 5000)
    })
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
</script>

<template>
  <div class="picker-page">
    <PageHero
      section="选股策略"
      number="03.6"
      title="财务选股"
      description="基于盈利能力（ROE、毛利率）与成长性（营收增长、净利润增长）的财务指标筛选。"
      meta="基本面"
    />

    <div class="filter-panel">
      <div class="filter-row">
        <div class="filter-item">
          <label>ROE ≥</label>
          <input v-model.number="filters.roe_min" type="number" step="0.1" />
        </div>
        <div class="filter-item">
          <label>毛利率 ≥</label>
          <input v-model.number="filters.gross_profit_ratio_min" type="number" step="0.1" />
        </div>
        <div class="filter-item">
          <label>净利率 ≥</label>
          <input v-model.number="filters.net_profit_ratio_min" type="number" step="0.1" placeholder="不限" />
        </div>
        <div class="filter-item">
          <label>净利润增长 ≥</label>
          <input v-model.number="filters.net_profit_yoy_min" type="number" step="0.1" />
        </div>
        <div class="filter-item">
          <label>营收增长 ≥</label>
          <input v-model.number="filters.revenue_yoy_min" type="number" step="0.1" />
        </div>
        <div class="filter-item">
          <label>负债率 ≤</label>
          <input v-model.number="filters.debt_ratio_max" type="number" step="0.1" />
        </div>
      </div>
      <div class="filter-row">
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
        <button class="btn-secondary" :disabled="syncLoading" @click="handleSync">
          {{ syncLoading ? '同步中...' : '同步财务数据' }}
        </button>
        <span v-if="syncMessage" class="sync-msg">{{ syncMessage }}</span>
      </div>
    </div>

    <div class="result-bar">共 {{ total }} 只</div>

    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th>股票</th>
            <th @click="handleSort('roe')">ROE {{ getSortIcon('roe') }}</th>
            <th @click="handleSort('gross_profit_ratio')">毛利率 {{ getSortIcon('gross_profit_ratio') }}</th>
            <th @click="handleSort('net_profit_ratio')">净利率 {{ getSortIcon('net_profit_ratio') }}</th>
            <th @click="handleSort('net_profit_yoy')">净利润增长 {{ getSortIcon('net_profit_yoy') }}</th>
            <th @click="handleSort('revenue_yoy')">营收增长 {{ getSortIcon('revenue_yoy') }}</th>
            <th @click="handleSort('debt_ratio')">负债率 {{ getSortIcon('debt_ratio') }}</th>
            <th>EPS</th>
            <th>BPS</th>
            <th>报告期</th>
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
            <td :class="{ 'highlight': item.roe >= 20 }">{{ item.roe?.toFixed(2) }}</td>
            <td>{{ item.gross_profit_ratio?.toFixed(2) }}</td>
            <td>{{ item.net_profit_ratio?.toFixed(2) }}</td>
            <td :class="{ 'up': item.net_profit_yoy > 0, 'down': item.net_profit_yoy < 0 }">
              {{ item.net_profit_yoy?.toFixed(2) }}
            </td>
            <td :class="{ 'up': item.revenue_yoy > 0, 'down': item.revenue_yoy < 0 }">
              {{ item.revenue_yoy?.toFixed(2) }}
            </td>
            <td>{{ item.debt_ratio?.toFixed(2) }}</td>
            <td>{{ item.eps?.toFixed(2) }}</td>
            <td>{{ item.bps?.toFixed(2) }}</td>
            <td>{{ item.report_date }}</td>
          </tr>
          <tr v-if="!loading && displayList.length === 0">
            <td colspan="10" class="empty">暂无数据，请调整筛选条件或同步财务数据</td>
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

.filter-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;

  label {
    font-size: 13px;
    color: #666;
    white-space: nowrap;
  }

  input[type="number"] {
    width: 80px;
    padding: 6px 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 13px;

    &:focus {
      outline: none;
      border-color: #409eff;
    }
  }

  &.checkbox label {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    font-size: 13px;
    color: #333;

    input {
      cursor: pointer;
    }
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}

.btn-primary {
  padding: 8px 20px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;

  &:hover {
    background: #66b1ff;
  }
}

.btn-secondary {
  padding: 8px 20px;
  background: #f5f7fa;
  color: #606266;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;

  &:hover:not(:disabled) {
    background: #ecf5ff;
    color: #409eff;
    border-color: #c6e2ff;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.sync-msg {
  font-size: 13px;
  color: #67c23a;
}

.table-wrapper {
  position: relative;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);

  th {
    background: #f5f7fa;
    padding: 12px 10px;
    text-align: right;
    font-weight: 600;
    color: #606266;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;

    &:first-child {
      text-align: left;
      padding-left: 16px;
    }

    &:last-child {
      padding-right: 16px;
    }

    &:hover {
      background: #e4e7ed;
    }
  }

  td {
    padding: 10px;
    text-align: right;
    border-bottom: 1px solid #ebeef5;

    &:first-child {
      text-align: left;
      padding-left: 16px;
    }

    &:last-child {
      padding-right: 16px;
    }
  }

  tr:hover td {
    background: #f5f7fa;
  }
}

.stock-name {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .symbol {
    font-weight: 600;
    color: #303133;
  }

  .name {
    font-size: 12px;
    color: #606266;
  }

  .industry {
    font-size: 11px;
    color: #909399;
  }
}

.highlight {
  color: #e6a23c;
  font-weight: 600;
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.loading-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #909399;
}
</style>
