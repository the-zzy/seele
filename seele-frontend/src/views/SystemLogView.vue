<script setup>
import { ref, onMounted } from 'vue'
import { systemLogApi } from '@/api/systemLog'
import PageHero from '@/components/common/PageHero.vue'
import BasePagination from '@/components/common/BasePagination.vue'

const activeTab = ref('errors')
const loading = ref(false)

const overview = ref({
  today_error_count: 0,
  today_operation_count: 0,
  latest_sync_logs: []
})

const errorLogs = ref({ list: [], total: 0 })
const operationLogs = ref({ list: [], total: 0 })
const syncLogs = ref({ list: [], total: 0 })

const errorQuery = ref({ page_num: 1, page_size: 10, level: '', source: '', days: 7 })
const operationQuery = ref({ page_num: 1, page_size: 10, operation_type: '', days: 7 })
const syncQuery = ref({ page_num: 1, page_size: 10, job_type: '', status: '', days: 7 })

const jobTypeMap = {
  stock_basic: '股票基础信息',
  daily: '日线数据',
  financial: '财务指标',
  indicator: '指标计算',
  board_list: '板块/ETF列表',
  board_daily: '板块/ETF日线',
  board_constituent: '板块成分股',
  index_daily: '指数日线',
  index_constituents: '指数成分股'
}

const statusMap = {
  running: '运行中',
  success: '成功',
  failed: '失败',
  skipped: '已跳过'
}

const statusClass = {
  running: 'status-running',
  success: 'status-success',
  failed: 'status-failed',
  skipped: 'status-skipped'
}

const levelClass = {
  error: 'level-error',
  warning: 'level-warning',
  critical: 'level-critical'
}

const operationTypeMap = {
  sync_manual: '手动同步',
  pipeline_start: '启动任务链',
  pipeline_cancel: '取消任务链',
  job_cancel: '取消任务'
}

async function loadOverview () {
  try {
    const res = await systemLogApi.getOverview()
    overview.value = res || { today_error_count: 0, today_operation_count: 0, latest_sync_logs: [] }
  } catch (error) {
    console.error('加载概览失败:', error)
  }
}

async function loadErrorLogs () {
  loading.value = true
  try {
    const res = await systemLogApi.getErrorLogs(errorQuery.value)
    errorLogs.value = res || { list: [], total: 0 }
  } catch (error) {
    console.error('加载错误日志失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadOperationLogs () {
  loading.value = true
  try {
    const res = await systemLogApi.getOperationLogs(operationQuery.value)
    operationLogs.value = res || { list: [], total: 0 }
  } catch (error) {
    console.error('加载操作日志失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadSyncLogs () {
  loading.value = true
  try {
    const res = await systemLogApi.getOverview()
    const list = res?.latest_sync_logs || []
    syncLogs.value = { list, total: list.length }
  } catch (error) {
    console.error('加载同步概览失败:', error)
  } finally {
    loading.value = false
  }
}

async function handleRefresh () {
  loading.value = true
  await loadOverview()
  if (activeTab.value === 'errors') await loadErrorLogs()
  if (activeTab.value === 'operations') await loadOperationLogs()
  if (activeTab.value === 'syncOverview') await loadSyncLogs()
  loading.value = false
}

function switchTab (tab) {
  activeTab.value = tab
  if (tab === 'errors' && errorLogs.value.list.length === 0) loadErrorLogs()
  if (tab === 'operations' && operationLogs.value.list.length === 0) loadOperationLogs()
  if (tab === 'syncOverview') loadSyncLogs()
}

function formatTime (ts) {
  if (!ts) return '-'
  return ts
}

function formatDuration (s) {
  if (s === null || s === undefined) return '-'
  if (s < 60) return `${s}秒`
  return `${Math.floor(s / 60)}分${s % 60}秒`
}

onMounted(() => {
  loadOverview()
  loadErrorLogs()
})
</script>

<template>
  <div class="system-log page">
    <PageHero
      section="系统管理"
      number="98"
      title="系统日志"
      description="查看系统错误、操作审计及同步任务最新状态。"
      meta="日志中心"
    >
      <template #actions>
        <button class="btn-refresh" :disabled="loading" @click="handleRefresh">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </template>
    </PageHero>

    <div class="content-wrap">
      <!-- 概览卡片 -->
      <div class="overview-cards">
        <div class="overview-card">
          <div class="card-label">今日错误</div>
          <div class="card-value" :class="overview.today_error_count > 0 ? 'text-error' : ''">
            {{ overview.today_error_count }}
          </div>
        </div>
        <div class="overview-card">
          <div class="card-label">今日操作</div>
          <div class="card-value">{{ overview.today_operation_count }}</div>
        </div>
        <div class="overview-card wide">
          <div class="card-label">各任务最新状态</div>
          <div class="sync-badges">
            <span
              v-for="log in overview.latest_sync_logs"
              :key="log.id"
              class="sync-badge"
              :class="statusClass[log.status]"
            >
              {{ jobTypeMap[log.job_type] || log.job_type }}
              <span class="badge-status">{{ statusMap[log.status] || log.status }}</span>
            </span>
            <span v-if="overview.latest_sync_logs.length === 0" class="text-muted">暂无记录</span>
          </div>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="tab-bar">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'errors' }"
          @click="switchTab('errors')"
        >
          错误日志
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'operations' }"
          @click="switchTab('operations')"
        >
          操作日志
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'syncOverview' }"
          @click="switchTab('syncOverview')"
        >
          同步任务概览
        </button>
      </div>

      <!-- 错误日志 -->
      <div v-show="activeTab === 'errors'" class="tab-panel">
        <div class="filter-bar">
          <select v-model="errorQuery.level" class="filter-select" @change="errorQuery.page_num = 1; loadErrorLogs()">
            <option value="">全部级别</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
          <select v-model="errorQuery.source" class="filter-select" @change="errorQuery.page_num = 1; loadErrorLogs()">
            <option value="">全部来源</option>
            <option value="sync_stock_basic_bg">股票基础同步</option>
            <option value="sync_financial_bg">财务指标同步</option>
            <option value="sync_indicator_bg">指标计算</option>
            <option value="sync_daily_bulk">日线批量</option>
            <option value="scheduler">定时任务</option>
          </select>
          <select v-model="errorQuery.days" class="filter-select" @change="errorQuery.page_num = 1; loadErrorLogs()">
            <option :value="1">今天</option>
            <option :value="3">最近3天</option>
            <option :value="7">最近7天</option>
            <option :value="30">最近30天</option>
          </select>
        </div>
        <div class="table-wrap">
          <table class="log-table">
            <thead>
              <tr>
                <th>级别</th>
                <th>来源</th>
                <th>消息</th>
                <th>关联ID</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in errorLogs.list" :key="row.id">
                <td>
                  <span class="level-tag" :class="levelClass[row.level]">{{ row.level }}</span>
                </td>
                <td>{{ row.source }}</td>
                <td :title="row.message">{{ row.message }}</td>
                <td>{{ row.trace_id || '-' }}</td>
                <td>{{ formatTime(row.created_at) }}</td>
              </tr>
              <tr v-if="errorLogs.list.length === 0 && !loading">
                <td colspan="5" class="empty">暂无错误日志</td>
              </tr>
            </tbody>
          </table>
        </div>
        <BasePagination
          v-model:page-num="errorQuery.page_num"
          v-model:page-size="errorQuery.page_size"
          :total="errorLogs.total"
          @update:page-num="loadErrorLogs"
          @update:page-size="loadErrorLogs"
        />
      </div>

      <!-- 操作日志 -->
      <div v-show="activeTab === 'operations'" class="tab-panel">
        <div class="filter-bar">
          <select v-model="operationQuery.operation_type" class="filter-select" @change="operationQuery.page_num = 1; loadOperationLogs()">
            <option value="">全部类型</option>
            <option value="sync_manual">手动同步</option>
            <option value="pipeline_start">启动任务链</option>
            <option value="pipeline_cancel">取消任务链</option>
            <option value="job_cancel">取消任务</option>
          </select>
          <select v-model="operationQuery.days" class="filter-select" @change="operationQuery.page_num = 1; loadOperationLogs()">
            <option :value="1">今天</option>
            <option :value="3">最近3天</option>
            <option :value="7">最近7天</option>
            <option :value="30">最近30天</option>
          </select>
        </div>
        <div class="table-wrap">
          <table class="log-table">
            <thead>
              <tr>
                <th>操作类型</th>
                <th>操作人</th>
                <th>目标</th>
                <th>详情</th>
                <th>结果</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in operationLogs.list" :key="row.id">
                <td>{{ operationTypeMap[row.operation_type] || row.operation_type }}</td>
                <td>{{ row.operator || '-' }}</td>
                <td>{{ row.target_type }} {{ row.target_id || '' }}</td>
                <td :title="row.detail">{{ row.detail || '-' }}</td>
                <td>
                  <span class="result-tag" :class="row.result === 'success' ? 'result-success' : 'result-failed'">
                    {{ row.result || '-' }}
                  </span>
                </td>
                <td>{{ formatTime(row.created_at) }}</td>
              </tr>
              <tr v-if="operationLogs.list.length === 0 && !loading">
                <td colspan="6" class="empty">暂无操作日志</td>
              </tr>
            </tbody>
          </table>
        </div>
        <BasePagination
          v-model:page-num="operationQuery.page_num"
          v-model:page-size="operationQuery.page_size"
          :total="operationLogs.total"
          @update:page-num="loadOperationLogs"
          @update:page-size="loadOperationLogs"
        />
      </div>

      <!-- 同步任务概览 -->
      <div v-show="activeTab === 'syncOverview'" class="tab-panel">
        <div class="filter-bar">
          <select v-model="syncQuery.days" class="filter-select" @change="syncQuery.page_num = 1; loadSyncLogs()">
            <option :value="1">今天</option>
            <option :value="3">最近3天</option>
            <option :value="7">最近7天</option>
            <option :value="30">最近30天</option>
          </select>
        </div>
        <div class="table-wrap">
          <table class="log-table">
            <thead>
              <tr>
                <th>任务类型</th>
                <th>触发方式</th>
                <th>状态</th>
                <th>开始时间</th>
                <th>耗时</th>
                <th>成功</th>
                <th>失败</th>
                <th>总计</th>
                <th>交易日</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in syncLogs.list" :key="log.id">
                <td>{{ jobTypeMap[log.job_type] || log.job_type }}</td>
                <td>
                  <span class="tag" :class="log.trigger_type === 'scheduled' ? 'tag-auto' : 'tag-manual'">
                    {{ log.trigger_type === 'scheduled' ? '定时' : '手动' }}
                  </span>
                </td>
                <td>
                  <span class="status-dot" :class="statusClass[log.status]">
                    {{ statusMap[log.status] || log.status }}
                  </span>
                </td>
                <td>{{ formatTime(log.started_at) }}</td>
                <td>{{ formatDuration(log.duration_seconds) }}</td>
                <td>{{ log.success_count ?? '-' }}</td>
                <td>{{ log.failed_count ?? '-' }}</td>
                <td>{{ log.total_count ?? '-' }}</td>
                <td>{{ log.trade_date || '-' }}</td>
              </tr>
              <tr v-if="syncLogs.list.length === 0 && !loading">
                <td colspan="9" class="empty">暂无同步记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.system-log {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
}

.content-wrap {
  flex: 1;
  overflow: auto;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  flex-shrink: 0;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
}

.overview-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;

  &.wide {
    grid-column: span 2;

    @media (max-width: 900px) {
      grid-column: span 1;
    }
  }

  .card-label {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .card-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    font-family: var(--font-mono);
    line-height: 1;

    &.text-error {
      color: var(--up);
    }
  }
}

.sync-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sync-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);

  &.status-running {
    background: var(--accent-subtle);
    color: var(--accent);
  }

  &.status-success {
    background: rgba(0, 180, 120, 0.1);
    color: var(--down);
  }

  &.status-failed {
    background: rgba(220, 60, 60, 0.1);
    color: var(--up);
  }
}

.badge-status {
  font-size: 10px;
  opacity: 0.8;
}

.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;
}

.tab-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  transition: all 0.2s;

  &.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  &:hover:not(.active) {
    color: var(--text-secondary);
  }
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.filter-select {
  padding: 7px 12px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
  outline: none;

  &:focus {
    border-color: var(--accent);
  }
}

.btn-refresh {
  padding: 7px 16px;
  background: var(--text-primary);
  color: var(--bg-primary);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 6px;
  flex-shrink: 0;
}

.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th, td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
  }

  th {
    position: sticky;
    top: 0;
    background: var(--bg-secondary);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    z-index: 1;
  }

  td {
    color: var(--text-secondary);
  }

  tr:hover td {
    background: var(--bg-secondary);
  }
}

.level-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;

  &.level-error {
    background: rgba(220, 60, 60, 0.1);
    color: var(--up);
  }

  &.level-warning {
    background: rgba(245, 166, 35, 0.1);
    color: #f5a623;
  }

  &.level-critical {
    background: rgba(180, 40, 40, 0.15);
    color: #b42828;
  }
}

.result-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;

  &.result-success {
    background: rgba(0, 180, 120, 0.1);
    color: var(--down);
  }

  &.result-failed {
    background: rgba(220, 60, 60, 0.1);
    color: var(--up);
  }
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;

  &.tag-auto {
    background: var(--accent-subtle);
    color: var(--accent);
  }

  &.tag-manual {
    background: var(--bg-tertiary);
    color: var(--text-muted);
  }
}

.status-dot {
  display: inline-flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }

  &.status-running::before {
    background: var(--accent);
  }

  &.status-success::before {
    background: var(--down);
  }

  &.status-failed::before {
    background: var(--up);
  }

  &.status-skipped::before {
    background: var(--text-muted);
  }
}

.empty {
  text-align: center;
  padding: 32px;
  color: var(--text-muted);
  font-size: 13px;
}

.text-muted {
  color: var(--text-muted);
  font-size: 12px;
}
</style>
