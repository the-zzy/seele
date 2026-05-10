<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { syncApi } from '@/api/stock'
import PageHero from '@/components/common/PageHero.vue'

const logs = ref([])
const loading = ref(false)
const syncing = ref({})
const days = ref(5)
const jobType = ref('')
const dbStatus = ref(null)
const detailedStatus = ref(null)
const syncDates = ref({ daily: '', indicator: '' })
const taskProgress = ref({})
const pollTimers = ref({})

function getTodayStr () {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const jobTypeMap = {
  stock_basic: '股票基础信息',
  daily: '日线数据',
  financial: '财务指标',
  indicator: '指标计算'
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

const taskGroups = computed(() => [
  {
    title: '数据同步',
    tasks: [
      {
        key: 'stock_basic',
        name: '股票基础信息',
        desc: '同步沪深A股基础信息、行业、流通市值等',
        api: () => syncApi.syncStockBasic()
      },
      {
        key: 'daily',
        name: '日线数据',
        desc: '按日期同步全部A股日线行情（开高低收量额等）',
        api: () => syncApi.syncByDate(syncDates.value.daily.replace(/-/g, '')),
        needDate: true,
        dateKey: 'daily'
      },
      {
        key: 'financial',
        name: '财务指标',
        desc: '同步全部股票最新一期财务指标数据',
        api: () => syncApi.syncFinancial()
      }
    ]
  },
  {
    title: '指标计算',
    tasks: [
      {
        key: 'indicator',
        name: '技术指标',
        desc: '计算均线、MACD、RSI、KDJ、BOLL等指标',
        api: () => syncApi.syncIndicator(syncDates.value.indicator),
        needDate: true,
        dateKey: 'indicator'
      }
    ]
  }
])

async function loadLogs () {
  loading.value = true
  try {
    const res = await syncApi.getJobLogs(days.value, jobType.value || null)
    logs.value = res?.list || []
  } catch (error) {
    console.error('加载任务日志失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadDbStatus () {
  try {
    const res = await syncApi.getDbStatus()
    dbStatus.value = res
  } catch (error) {
    console.error('加载数据库状态失败:', error)
  }
}

async function loadDetailedStatus () {
  try {
    const res = await syncApi.getDetailedStatus()
    detailedStatus.value = res
  } catch (error) {
    console.error('加载详细同步状态失败:', error)
  }
}

function clearPoll (key) {
  if (pollTimers.value[key]) {
    clearInterval(pollTimers.value[key])
    delete pollTimers.value[key]
  }
}

async function pollTaskStatus (taskKey, taskId) {
  clearPoll(taskKey)
  taskProgress.value[taskKey] = { current: 0, total: 0, status: 'running' }

  const doPoll = async () => {
    try {
      const res = await syncApi.getTaskStatus(taskId)
      const data = res || {}
      const progress = data.progress || { current: 0, total: 0 }
      taskProgress.value[taskKey] = {
        current: progress.current || 0,
        total: progress.total || 0,
        status: data.status || 'running'
      }

      if (data.status === 'success' || data.status === 'failed') {
        clearPoll(taskKey)
        syncing.value[taskKey] = false
        await loadLogs()
        if (taskKey === 'stock_basic' || taskKey === 'daily' || taskKey === 'indicator') {
          await loadDbStatus()
        }
      }
    } catch (err) {
      console.error('轮询任务状态失败:', err)
    }
  }

  await doPoll()
  pollTimers.value[taskKey] = setInterval(doPoll, 2000)
}

async function handleManualSync (task) {
  if (syncing.value[task.key]) return
  syncing.value[task.key] = true
  try {
    const res = await task.api()
    const taskId = res?.task_id
    if (taskId) {
      await pollTaskStatus(task.key, taskId)
    } else {
      alert(res?.summary || res?.message || '同步任务已提交')
      syncing.value[task.key] = false
      await loadLogs()
    }
  } catch (error) {
    alert('同步失败: ' + (error.response?.data?.detail || error.message))
    syncing.value[task.key] = false
  }
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

function formatNumber (n) {
  if (n === null || n === undefined) return '-'
  if (n >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (n >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString()
}

function formatDate (dateStr) {
  if (!dateStr) return '-'
  return dateStr
}

async function initDefaultDates () {
  try {
    const latest = await syncApi.getLatestTradeDate()
    const dateStr = latest || getTodayStr()
    syncDates.value.daily = dateStr
    syncDates.value.indicator = dateStr
  } catch (error) {
    const today = getTodayStr()
    syncDates.value.daily = today
    syncDates.value.indicator = today
  }
}

onMounted(() => {
  initDefaultDates()
  loadLogs()
  loadDbStatus()
  loadDetailedStatus()
})

onUnmounted(() => {
  Object.keys(pollTimers.value).forEach(clearPoll)
})
</script>

<template>
  <div class="sync-job-log page">
    <PageHero
      section="系统管理"
      number="99"
      title="同步任务"
      description="查看定时任务和手动任务的最近执行记录及状态统计。"
      meta="任务日志"
    >
      <template #actions>
        <div class="filter-bar">
          <select v-model="jobType" class="filter-select" @change="loadLogs">
            <option value="">全部类型</option>
            <option value="stock_basic">股票基础信息</option>
            <option value="daily">日线数据</option>
            <option value="financial">财务指标</option>
            <option value="indicator">指标计算</option>
          </select>
          <select v-model="days" class="filter-select" @change="loadLogs">
            <option :value="3">最近3天</option>
            <option :value="5">最近5天</option>
            <option :value="7">最近7天</option>
            <option :value="30">最近30天</option>
          </select>
          <button class="btn-refresh" :disabled="loading" @click="loadLogs">
            {{ loading ? '加载中...' : '刷新' }}
          </button>
        </div>
      </template>
    </PageHero>

    <div class="content-wrap">
      <div class="top-section">
        <div class="db-status-card" v-if="dbStatus">
          <h3 class="card-title">数据库状态</h3>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">股票基础</span>
              <span class="status-value">{{ formatNumber(dbStatus.stock_basic_count) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">日线数据</span>
              <span class="status-value">{{ formatNumber(dbStatus.stock_daily_count) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">技术指标</span>
              <span class="status-value">{{ formatNumber(dbStatus.indicator_count) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">财务指标</span>
              <span class="status-value">{{ formatNumber(dbStatus.financial_count) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">最新交易日</span>
              <span class="status-value">{{ dbStatus.latest_trade_date || '-' }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">最新指标日</span>
              <span class="status-value">{{ dbStatus.latest_indicator_date || '-' }}</span>
            </div>
          </div>
        </div>

        <div class="task-groups">
          <div v-for="group in taskGroups" :key="group.title" class="task-group">
            <h3 class="group-title">{{ group.title }}</h3>
            <div class="task-list">
              <div v-for="task in group.tasks" :key="task.key" class="task-card">
                <div class="task-info">
                  <span class="task-name">{{ task.name }}</span>
                  <span class="task-desc">{{ task.desc }}</span>
                </div>
                <div class="task-action">
                  <input
                    v-if="task.needDate"
                    v-model="syncDates[task.dateKey]"
                    type="date"
                    class="date-input"
                  />
                  <button
                    class="btn-sync"
                    :disabled="syncing[task.key] || (task.needDate && !syncDates[task.dateKey])"
                    @click="handleManualSync(task)"
                  >
                    {{ syncing[task.key]
                      ? (taskProgress[task.key]?.total > 0
                        ? `同步中 ${taskProgress[task.key].current}/${taskProgress[task.key].total}`
                        : '同步中...')
                      : '手动同步' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模块7：同步任务数据库状态 -->
      <div v-if="detailedStatus" class="detail-section">
        <h3 class="section-title">同步数据库状态</h3>
        <div class="detail-grid">
          <!-- 股票基本信息 -->
          <div class="detail-card">
            <div class="detail-card-header">
              <span class="detail-card-title">股票基本信息</span>
              <span class="detail-card-meta">上次同步: {{ formatTime(detailedStatus.stock_basic.last_sync) }}</span>
            </div>
            <div class="detail-metrics">
              <div class="metric">
                <span class="metric-value">{{ formatNumber(detailedStatus.stock_basic.total) }}</span>
                <span class="metric-label">总记录</span>
              </div>
              <div class="metric">
                <span class="metric-value highlight">{{ formatNumber(detailedStatus.stock_basic.valid_count) }}</span>
                <span class="metric-label">有效记录(非ST非退市)</span>
              </div>
              <div class="metric">
                <span class="metric-value warn">{{ formatNumber(detailedStatus.stock_basic.st_count) }}</span>
                <span class="metric-label">ST股票</span>
              </div>
              <div class="metric">
                <span class="metric-value danger">{{ formatNumber(detailedStatus.stock_basic.delisted_count) }}</span>
                <span class="metric-label">退市股票</span>
              </div>
            </div>
            <div class="market-dist">
              <div
                v-for="(count, market) in detailedStatus.stock_basic.market_distribution"
                :key="market"
                class="market-item"
              >
                <span class="market-name">{{ market }}</span>
                <span class="market-bar-wrap">
                  <span
                    class="market-bar"
                    :style="{ width: `${(count / detailedStatus.stock_basic.total) * 100}%` }"
                  />
                </span>
                <span class="market-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <!-- 日线与指标 -->
          <div class="detail-card wide">
            <div class="detail-card-header">
              <span class="detail-card-title">日线记录与指标计算（最近5个交易日）</span>
              <span class="detail-card-meta">应同步: {{ formatNumber(detailedStatus.stock_basic.valid_count) }} 只</span>
            </div>
            <div class="daily-table-wrap">
              <table class="daily-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>日线记录</th>
                    <th>指标记录</th>
                    <th>daily日志</th>
                    <th>indicator日志</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in detailedStatus.daily" :key="row.date">
                    <td>{{ formatDate(row.date) }}</td>
                    <td>
                      <span :class="row.daily_count > 0 ? 'num-ok' : 'num-zero'">{{ row.daily_count }}</span>
                    </td>
                    <td>
                      <span :class="row.indicator_count > 0 ? 'num-ok' : 'num-zero'">{{ row.indicator_count }}</span>
                    </td>
                    <td>
                      <template v-if="row.daily_log">
                        <span class="tag" :class="`tag-${row.daily_log.status}`">{{ row.daily_log.status }}</span>
                        <span class="log-count">
                          {{ row.daily_log.success ?? 0 }} / {{ row.daily_log.failed ?? 0 }} / {{ row.daily_log.total ?? 0 }}
                        </span>
                      </template>
                      <span v-else class="text-muted">无日志</span>
                    </td>
                    <td>
                      <template v-if="row.indicator_log">
                        <span class="tag" :class="`tag-${row.indicator_log.status}`">{{ row.indicator_log.status }}</span>
                        <span class="log-count">
                          {{ row.indicator_log.success ?? 0 }} / {{ row.indicator_log.failed ?? 0 }} / {{ row.indicator_log.total ?? 0 }}
                        </span>
                      </template>
                      <span v-else class="text-muted">无日志</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 财报指标 -->
          <div class="detail-card">
            <div class="detail-card-header">
              <span class="detail-card-title">财报指标</span>
              <span class="detail-card-meta">上次同步: {{ formatTime(detailedStatus.financial.last_sync) }}</span>
            </div>
            <div class="detail-metrics">
              <div class="metric">
                <span class="metric-value">{{ formatNumber(detailedStatus.financial.total) }}</span>
                <span class="metric-label">已获取</span>
              </div>
              <div class="metric">
                <span class="metric-value">{{ formatNumber(detailedStatus.financial.expected) }}</span>
                <span class="metric-label">应获取</span>
              </div>
              <div class="metric">
                <span class="metric-value danger">{{ formatNumber(detailedStatus.financial.missing) }}</span>
                <span class="metric-label">缺失</span>
              </div>
            </div>
            <div class="report-dist">
              <div class="report-dist-title">报告期分布</div>
              <div
                v-for="item in detailedStatus.financial.report_distribution"
                :key="item.date"
                class="report-item"
              >
                <span class="report-date">{{ item.date }}</span>
                <span class="report-bar-wrap">
                  <span
                    class="report-bar"
                    :style="{ width: `${(item.count / detailedStatus.financial.total) * 100}%` }"
                  />
                </span>
                <span class="report-count">{{ item.count }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="table-section">
        <h3 class="section-title">最近执行记录</h3>
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
                <th>跳过</th>
                <th>总计</th>
                <th>交易日</th>
                <th>错误信息</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in logs" :key="log.id">
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
                <td>{{ log.skipped_count ?? '-' }}</td>
                <td>{{ log.total_count ?? '-' }}</td>
                <td>{{ log.trade_date || '-' }}</td>
                <td class="error-cell" :title="log.error_message">
                  {{ log.error_message || '-' }}
                </td>
              </tr>
              <tr v-if="logs.length === 0 && !loading">
                <td colspan="11" class="empty">暂无任务记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.sync-job-log {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 4px 28px 18px;
  box-sizing: border-box;
  overflow: hidden;
}

.content-wrap {
  flex: 1;
  overflow: auto;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.top-section {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  min-height: 0;
}

.db-status-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px;

  .card-title {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-primary);
    margin: 0 0 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--rule);
  }
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .status-label {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .status-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }
}

.task-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-group {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px;
}

.group-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  gap: 12px;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;

  .task-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .task-desc {
    font-size: 11px;
    color: var(--text-muted);
  }
}

.task-action {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.date-input {
  padding: 6px 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;

  &:focus {
    border-color: var(--accent);
  }
}

.btn-sync {
  padding: 6px 14px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  white-space: nowrap;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

.table-section {
  .section-title {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-primary);
    margin: 0 0 12px;
  }
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
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

.error-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
}

@media (max-width: 1200px) {
  .top-section {
    grid-template-columns: 1fr;
  }
}

/* 模块7：同步数据库状态 */
.detail-section {
  margin-top: 4px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 320px 1fr 320px;
  gap: 16px;
}

.detail-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}

.detail-card-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-primary);
}

.detail-card-meta {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.detail-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: var(--bg-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 8px 10px;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.metric-value.highlight {
  color: var(--accent);
}

.metric-value.warn {
  color: #f5a623;
}

.metric-value.danger {
  color: var(--up);
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
}

.market-dist {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.market-item {
  display: grid;
  grid-template-columns: 60px 1fr 40px;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.market-name {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.market-bar-wrap {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.market-bar {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
}

.market-count {
  text-align: right;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 600;
}

.daily-table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 4px;
}

.daily-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th, td {
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
  }

  th {
    background: var(--bg-primary);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  td {
    color: var(--text-secondary);
  }

  tr:last-child td {
    border-bottom: none;
  }
}

.num-ok {
  color: var(--down);
  font-weight: 600;
}

.num-zero {
  color: var(--text-muted);
}

.log-count {
  margin-left: 8px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.text-muted {
  color: var(--text-muted);
  font-size: 11px;
}

.tag-running {
  background: var(--accent-subtle);
  color: var(--accent);
}

.tag-success {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.tag-failed {
  background: rgba(244, 67, 54, 0.15);
  color: #f44336;
}

.tag-skipped {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.report-dist {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.report-dist-title {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  margin-bottom: 2px;
}

.report-item {
  display: grid;
  grid-template-columns: 90px 1fr 40px;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.report-date {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.report-bar-wrap {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.report-bar {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
}

.report-count {
  text-align: right;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 600;
}

@media (max-width: 1400px) {
  .detail-grid {
    grid-template-columns: 1fr 1fr;
  }
  .detail-card.wide {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
  .detail-card.wide {
    grid-column: auto;
  }
}
</style>
