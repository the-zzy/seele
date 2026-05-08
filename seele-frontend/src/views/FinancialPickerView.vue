<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { financialApi } from '@/api/financial'
import { useStockPicker } from '@/composables/useStockPicker'
import BasePagination from '@/components/common/BasePagination.vue'
import PageHero from '@/components/common/PageHero.vue'
import SyncProgress from '@/components/common/SyncProgress.vue'

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

const syncing = ref(false)
const syncProgress = ref({
  visible: false,
  percent: 0,
  current: 0,
  total: 0,
  message: ''
})
let syncEventSource = null

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
  if (!confirm('确定要同步全部股票的财务指标数据吗？\n同步任务将在后台异步执行，可实时查看进度。')) {
    return
  }

  if (syncEventSource) {
    syncEventSource.close()
    syncEventSource = null
  }

  syncing.value = true
  syncProgress.value = {
    visible: true,
    percent: 0,
    current: 0,
    total: 0,
    message: '正在连接...'
  }

  const es = financialApi.createFinancialSyncStream()
  syncEventSource = es

  es.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      if (payload.status === 'running') {
        const current = payload.current || 0
        const total = payload.total || 0
        syncProgress.value = {
          visible: true,
          percent: total ? Math.round(current / total * 100) : 0,
          current,
          total,
          message: payload.symbol
            ? `正在同步: ${payload.symbol}`
            : '正在同步财务数据...'
        }
      } else if (payload.status === 'completed') {
        const result = payload.result || {}
        syncProgress.value = {
          visible: true,
          percent: 100,
          current: result.upserted || 0,
          total: result.total_stocks || 0,
          message: result.summary || '同步完成'
        }
        es.close()
        syncEventSource = null
        syncing.value = false
        search({})
        setTimeout(() => {
          syncProgress.value.visible = false
        }, 3000)
      } else if (payload.status === 'failed') {
        syncProgress.value = {
          visible: true,
          percent: 0,
          current: 0,
          total: 0,
          message: '同步失败: ' + (payload.error || '未知错误')
        }
        es.close()
        syncEventSource = null
        syncing.value = false
      }
    } catch (e) {
      console.error('解析进度消息失败:', e)
    }
  }

  es.onerror = () => {
    syncProgress.value.message = '连接异常，请刷新页面查看结果'
    es.close()
    syncEventSource = null
    syncing.value = false
  }
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
        <button class="btn-secondary" :disabled="syncing" @click="handleSync">
          {{ syncing ? '同步中...' : '同步财务数据' }}
        </button>
      </div>
      <SyncProgress
        :visible="syncProgress.visible"
        :percent="syncProgress.percent"
        :current="syncProgress.current"
        :total="syncProgress.total"
        :message="syncProgress.message"
      />
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
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-soft);
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
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
    white-space: nowrap;
  }

  input[type="number"] {
    width: 80px;
    padding: 6px 8px;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    font-size: 13px;
    color: var(--text-primary);
    transition: border-color 0.2s;

    &:focus {
      outline: none;
      border-color: var(--accent);
    }

    &::placeholder {
      color: var(--text-faint);
    }
  }

  &.checkbox label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text-secondary);
    padding: 4px 10px;
    border: 1px solid var(--rule);
    border-radius: 999px;
    transition: all 0.18s;

    input {
      cursor: pointer;
      width: 12px;
      height: 12px;
      margin: 0;
      accent-color: var(--accent);
    }

    &:hover {
      border-color: var(--text-faint);
      color: var(--text-primary);
    }

    &:has(input:checked) {
      background: var(--accent-subtle);
      border-color: rgba(59, 130, 246, 0.35);
      color: var(--text-primary);
    }
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
}

.btn-primary {
  padding: 8px 18px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: background 0.2s;

  &:hover {
    background: var(--accent-hover);
  }
}

.btn-secondary {
  padding: 8px 18px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: var(--accent-subtle);
    color: var(--accent);
    border-color: var(--accent);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.table-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--bg-secondary);
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

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;

  th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--bg-primary);
    padding: 12px 10px;
    text-align: right;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    border-bottom: 1px solid var(--rule);

    &:first-child {
      text-align: left;
      padding-left: 16px;
    }

    &:last-child {
      padding-right: 16px;
    }

    &:hover {
      color: var(--text-secondary);
    }
  }

  td {
    padding: 10px;
    text-align: right;
    border-bottom: 1px solid var(--rule);
    color: var(--text-primary);

    &:first-child {
      text-align: left;
      padding-left: 16px;
    }

    &:last-child {
      padding-right: 16px;
    }
  }

  tbody tr {
    cursor: pointer;
    transition: background 0.12s;

    &:hover td {
      background: var(--bg-tertiary);
    }
  }
}

.stock-name {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .symbol {
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: 0.04em;
  }

  .name {
    font-family: var(--font-body);
    font-size: 12px;
    color: var(--text-secondary);
  }

  .industry {
    font-size: 11px;
    color: var(--text-muted);
  }
}

.highlight {
  color: var(--accent);
  font-weight: 600;
}

.up {
  color: var(--up);
}

.down {
  color: var(--down);
}

.empty {
  text-align: center;
  color: var(--text-faint);
  padding: 40px 0;
}

.loading-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: color-mix(in srgb, var(--bg-primary) 88%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--text-muted);
  z-index: 2;
}
</style>
