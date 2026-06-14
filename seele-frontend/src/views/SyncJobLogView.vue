<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { toast } from '@/composables/useToast'
import { syncApi, tradeCalendarApi } from '@/api/stock'
import { useSyncTask } from '@/composables/useSyncTask'
import PageHero from '@/components/common/PageHero.vue'
import BasePagination from '@/components/common/BasePagination.vue'

const detailedStatus = ref(null)
const dailyTotal = ref(0)
const dailyPageNum = ref(1)
const dailyPageSize = ref(10)
const incrementalMap = ref({})

const { syncing, progress: taskProgress, startSync, restoreTasks, clearPoll } = useSyncTask()

const pipeline = ref(null)
const pipelinePollTimer = ref(null)
const pipelineLoading = ref(false)

const pipelineDateMap = ref({
  daily: '',
  full: '',
  board: ''
})

async function loadLatestTradeDate () {
  try {
    const date = await tradeCalendarApi.getLatest()
    if (date) {
      pipelineDateMap.value.daily = date
      pipelineDateMap.value.full = date
      pipelineDateMap.value.board = date
    }
  } catch (_) {
    // 静默失败，用户可手动输入日期
  }
}

const chainDefinitions = {
  daily: {
    label: '每日更新',
    desc: '股票基础 → 日线 → 指标',
    steps: ['股票基础信息', '日线数据', '指标计算']
  },
  full: {
    label: '全量更新',
    desc: '基础 → 日线 → 指标 → 财务 → 板块 → 指数',
    steps: ['股票基础信息', '日线数据', '指标计算', '财务指标', '板块/ETF列表', '板块/ETF日线', '板块成分股', '指数日线', '指数成分股']
  },
  board: {
    label: '板块更新',
    desc: '板块列表 → 板块日线 → 成分股',
    steps: ['板块/ETF列表', '板块/ETF日线', '板块成分股']
  }
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

const onSyncDone = async () => {
  await loadDetailedStatus()
}

async function startPipelineSync (chainType) {
  if (pipelineLoading.value) return
  pipelineLoading.value = true
  try {
    const tradeDate = pipelineDateMap.value[chainType] || null
    const res = await syncApi.startPipeline(chainType, tradeDate)
    const pipelineId = res?.pipeline_id
    if (pipelineId) {
      pipeline.value = {
        pipeline_id: pipelineId,
        chain_type: chainType,
        status: 'running',
        steps: []
      }
      pollPipeline(pipelineId)
    }
  } catch (error) {
    toast.error('启动任务链失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    pipelineLoading.value = false
  }
}

function pollPipeline (pipelineId) {
  stopPipelinePoll()
  const doPoll = async () => {
    try {
      const data = await syncApi.getPipeline(pipelineId)
      pipeline.value = data
      if (data?.status === 'success' || data?.status === 'failed') {
        stopPipelinePoll()
        await loadDetailedStatus()
      }
    } catch (err) {
      console.error('轮询任务链失败:', err)
    }
  }
  doPoll()
  pipelinePollTimer.value = setInterval(doPoll, 2000)
}

function stopPipelinePoll () {
  if (pipelinePollTimer.value) {
    clearInterval(pipelinePollTimer.value)
    pipelinePollTimer.value = null
  }
}

async function handleCancelPipeline () {
  if (!pipeline.value?.pipeline_id) return
  if (!confirm('确定要停止当前任务链吗？')) return
  try {
    await syncApi.cancelPipeline(pipeline.value.pipeline_id)
    stopPipelinePoll()
  } catch (error) {
    toast.error('取消失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function restorePipeline () {
  try {
    const res = await syncApi.getPipelines()
    const active = res?.pipelines?.find(p => p.status === 'running')
    if (active) {
      const detail = await syncApi.getPipeline(active.pipeline_id)
      pipeline.value = detail
      pollPipeline(active.pipeline_id)
    }
  } catch (e) {
    console.error('恢复任务链失败:', e)
  }
}

async function loadDetailedStatus () {
  try {
    const res = await syncApi.getDetailedStatus(dailyPageNum.value, dailyPageSize.value)
    detailedStatus.value = res
    dailyTotal.value = res?.daily_total || 0
  } catch (error) {
    console.error('加载详细同步状态失败:', error)
  }
}

async function handleRefresh () {
  await loadDetailedStatus()
}

async function handleDailyPageChange (newPage) {
  dailyPageNum.value = newPage
  await loadDetailedStatus()
}

async function handleDailyPageSizeChange (newSize) {
  dailyPageSize.value = newSize
  dailyPageNum.value = 1
  await loadDetailedStatus()
}

async function handleDailySync (date) {
  const taskKey = `daily_${date.replace(/-/g, '')}`
  const incremental = incrementalMap.value[date]
  await startSync(taskKey, () => syncApi.syncByDate(date, incremental), {
    checkExisting: true,
    onDone: onSyncDone
  })
}

async function handleIndicatorSync (date) {
  const taskKey = `indicator_${date.replace(/-/g, '')}`
  const incremental = incrementalMap.value[date]
  await startSync(taskKey, () => syncApi.syncIndicator(date, incremental), {
    checkExisting: true,
    onDone: onSyncDone
  })
}

function formatTime (ts) {
  if (!ts) return '-'
  return ts
}

function formatNumber (n) {
  if (n === null || n === undefined) return '-'
  if (n >= 100000000) return `${(n / 100000000).toFixed(2)}亿`
  if (n >= 10000) return `${(n / 10000).toFixed(2)}万`
  return n.toLocaleString()
}

onMounted(async () => {
  await loadLatestTradeDate()
  await loadDetailedStatus()

  // 恢复正在运行的同步任务跟踪
  await restoreTasks([
    (task) => task.job_type === 'stock_basic' ? 'stock_basic' : null,
    (task) => task.job_type === 'daily' ? 'daily_' + task.trade_date : null,
    (task) => task.job_type === 'indicator' ? 'indicator_' + task.trade_date : null,
    (task) => task.job_type === 'financial' ? 'financial' : null
  ], { onDone: onSyncDone })

  // 恢复正在运行的任务链
  await restorePipeline()
})

onUnmounted(() => {
  stopPipelinePoll()
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
        <button class="btn-refresh" @click="handleRefresh">刷新</button>
      </template>
    </PageHero>

    <div class="content-wrap">
      <!-- 一键同步区域 -->
      <div class="pipeline-section">
        <div class="pipeline-cards">
          <div
            v-for="(cfg, key) in chainDefinitions"
            :key="key"
            class="pipeline-card"
          >
            <div class="pipeline-card-header">
              <span class="pipeline-card-title">{{ cfg.label }}</span>
              <span class="pipeline-card-desc">{{ cfg.desc }}</span>
            </div>
            <div class="pipeline-steps-preview">
              <span
                v-for="(s, idx) in cfg.steps"
                :key="idx"
                class="step-tag"
              >{{ s }}</span>
            </div>
            <div class="pipeline-date-row">
              <input
                v-model="pipelineDateMap[key]"
                type="date"
                class="pipeline-date-input"
              >
              <button
                class="btn-pipeline-start"
                :disabled="pipelineLoading || (pipeline && pipeline.status === 'running')"
                @click="startPipelineSync(key)"
              >
                {{ pipelineLoading ? '启动中...' : '启动' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 执行中状态面板 -->
        <div v-if="pipeline" class="pipeline-status-panel">
          <div class="pipeline-status-header">
            <span class="pipeline-status-title">
              {{ chainDefinitions[pipeline.chain_type]?.label || pipeline.chain_type }}
              <span :class="['pipeline-status-badge', 'status-' + pipeline.status]">
                {{ statusMap[pipeline.status] || pipeline.status }}
              </span>
            </span>
            <button
              v-if="pipeline.status === 'running'"
              class="btn-pipeline-cancel"
              @click="handleCancelPipeline"
            >
              停止
            </button>
          </div>
          <div class="pipeline-steps">
            <div
              v-for="(step, idx) in pipeline.steps"
              :key="idx"
              class="pipeline-step"
              :class="'step-' + step.status"
            >
              <span class="step-index">{{ idx + 1 }}</span>
              <span class="step-name">{{ step.name }}</span>
              <span class="step-status-icon" :class="'icon-' + step.status">
                <template v-if="step.status === 'running'">
                  <span class="spinner" />
                </template>
                <template v-else-if="step.status === 'success'">&#10003;</template>
                <template v-else-if="step.status === 'failed'">&#10007;</template>
                <template v-else>&#9675;</template>
              </span>
              <span v-if="step.error" class="step-error" :title="step.error">{{ step.error }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="top-section">
        <div class="left-cards">
          <div class="stock-basic-card" v-if="detailedStatus">
            <div class="stock-basic-header">
              <h3 class="card-title">股票基础信息</h3>
            </div>
            <div class="stock-basic-total">
              <span class="total-value">{{ formatNumber(detailedStatus.stock_basic.total) }}</span>
              <span class="total-label">只股票</span>
            </div>
            <div class="stock-basic-meta">
              <span class="meta-item">
                <span class="meta-dot valid"></span>
                有效 {{ formatNumber(detailedStatus.stock_basic.valid_count) }}
              </span>
              <span class="meta-item">
                <span class="meta-dot st"></span>
                ST {{ formatNumber(detailedStatus.stock_basic.st_count) }}
              </span>
              <span class="meta-item">
                <span class="meta-dot delisted"></span>
                退市 {{ formatNumber(detailedStatus.stock_basic.delisted_count) }}
              </span>
            </div>
            <div class="market-list">
              <div
                v-for="(count, market) in detailedStatus.stock_basic.market_distribution"
                :key="market"
                class="market-row"
              >
                <span class="market-name">{{ market }}</span>
                <span class="market-bar-wrap">
                  <span
                    class="market-bar"
                    :style="{ width: `${(count / detailedStatus.stock_basic.total) * 100}%` }"
                  />
                </span>
                <span class="market-count">{{ formatNumber(count) }}</span>
              </div>
            </div>
            <div class="last-sync">
              最近同步: {{ formatTime(detailedStatus.stock_basic.last_sync) }}
            </div>
          </div>

          <div class="stock-basic-card" v-if="detailedStatus?.board">
            <div class="stock-basic-header">
              <h3 class="card-title">板块/ETF</h3>
            </div>
            <div class="stock-basic-total">
              <span class="total-value">{{ formatNumber(detailedStatus.board.total) }}</span>
              <span class="total-label">个板块/ETF</span>
            </div>
            <div class="stock-basic-meta">
              <span class="meta-item">
                <span class="meta-dot valid"></span>
                行业 {{ formatNumber(detailedStatus.board.industry_count) }}
              </span>
              <span class="meta-item">
                <span class="meta-dot concept"></span>
                概念 {{ formatNumber(detailedStatus.board.concept_count) }}
              </span>
              <span class="meta-item">
                <span class="meta-dot etf"></span>
                ETF {{ formatNumber(detailedStatus.board.etf_count) }}
              </span>
            </div>
            <div class="market-list">
              <div class="market-row">
                <span class="market-name">行业</span>
                <span class="market-bar-wrap">
                  <span
                    class="market-bar"
                    :style="{ width: `${(detailedStatus.board.industry_count / detailedStatus.board.total) * 100}%` }"
                  />
                </span>
                <span class="market-count">{{ formatNumber(detailedStatus.board.industry_count) }}</span>
              </div>
              <div class="market-row">
                <span class="market-name">概念</span>
                <span class="market-bar-wrap">
                  <span
                    class="market-bar"
                    :style="{ width: `${(detailedStatus.board.concept_count / detailedStatus.board.total) * 100}%` }"
                  />
                </span>
                <span class="market-count">{{ formatNumber(detailedStatus.board.concept_count) }}</span>
              </div>
              <div class="market-row">
                <span class="market-name">ETF</span>
                <span class="market-bar-wrap">
                  <span
                    class="market-bar"
                    :style="{ width: `${(detailedStatus.board.etf_count / detailedStatus.board.total) * 100}%` }"
                  />
                </span>
                <span class="market-count">{{ formatNumber(detailedStatus.board.etf_count) }}</span>
              </div>
            </div>
            <div class="last-sync">
              最近同步: {{ formatTime(detailedStatus.board.last_sync) }}
              <span v-if="detailedStatus.board.latest_daily_date" class="last-sync-extra">
                · 日线至 {{ detailedStatus.board.latest_daily_date }}
              </span>
            </div>
            <div class="last-sync-extra-row">
              成分股 {{ formatNumber(detailedStatus.board.constituent_count) }} 条
            </div>
          </div>
        </div>

        <div class="daily-section" v-if="detailedStatus">
          <div class="daily-section-header">
            <h3 class="section-title">最近十个交易日</h3>
            <span class="section-note">统计范围不含北交所 · 每页 10 条</span>
          </div>
          <div class="daily-table-wrap">
            <table class="daily-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>总股票数</th>
                  <th>日线数据</th>
                  <th>指标数据</th>
                  <th>增量更新</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in detailedStatus.daily" :key="row.date">
                  <td>{{ row.date }}</td>
                  <td>
                    <span :class="row.total_stock_count > 0 ? 'num-ok' : 'num-zero'">
                      {{ row.total_stock_count }}
                    </span>
                  </td>
                  <td>
                    <span :class="row.daily_count > 0 ? 'num-ok' : 'num-zero'">
                      {{ row.daily_count }}
                      <small v-if="row.missing_daily > 0" class="missing-tag">缺{{ row.missing_daily }}</small>
                    </span>
                  </td>
                  <td>
                    <span :class="row.indicator_count > 0 ? 'num-ok' : 'num-zero'">
                      {{ row.indicator_count }}
                      <small v-if="row.missing_indicator > 0" class="missing-tag">缺{{ row.missing_indicator }}</small>
                    </span>
                  </td>
                  <td class="col-incremental">
                    <label class="toggle-label">
                      <input
                        type="checkbox"
                        v-model="incrementalMap[row.date]"
                      >
                      <span class="toggle-text">{{ incrementalMap[row.date] ? '增量' : '全量' }}</span>
                    </label>
                  </td>
                  <td>
                    <div class="action-btns">
                      <button
                        class="btn-sync-small"
                        :disabled="syncing['daily_' + row.date.replace(/-/g, '')]"
                        @click="handleDailySync(row.date)"
                      >
                        {{ syncing['daily_' + row.date.replace(/-/g, '')]
                          ? (taskProgress['daily_' + row.date.replace(/-/g, '')]?.total > 0
                            ? `同步中 ${taskProgress['daily_' + row.date.replace(/-/g, '')].current}/${taskProgress['daily_' + row.date.replace(/-/g, '')].total}`
                            : '同步中...')
                          : '日线同步' }}
                      </button>
                      <button
                        class="btn-sync-small"
                        :disabled="syncing['indicator_' + row.date.replace(/-/g, '')]"
                        @click="handleIndicatorSync(row.date)"
                      >
                        {{ syncing['indicator_' + row.date.replace(/-/g, '')]
                          ? (taskProgress['indicator_' + row.date.replace(/-/g, '')]?.total > 0
                            ? `计算中 ${taskProgress['indicator_' + row.date.replace(/-/g, '')].current}/${taskProgress['indicator_' + row.date.replace(/-/g, '')].total}`
                            : '计算中...')
                          : '指标计算' }}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <BasePagination
            v-if="dailyTotal > 0"
            :page-num="dailyPageNum"
            :page-size="dailyPageSize"
            :total="dailyTotal"
            @update:page-num="handleDailyPageChange"
            @update:page-size="handleDailyPageSizeChange"
          />
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

  @media (max-width: 768px) {
    padding: 4px 16px 12px;
  }
}

.content-wrap {
  flex: 1;
  overflow: auto;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.top-section {
  display: grid;
  grid-template-columns: minmax(280px, 30%) 1fr;
  gap: 20px;
  min-height: 0;
}

.left-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.stock-basic-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;

  .stock-basic-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--rule);
  }

  .card-title {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-primary);
    margin: 0;
  }

  .stock-basic-total {
    display: flex;
    align-items: baseline;
    gap: 6px;

    .total-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);
      font-family: var(--font-mono);
      line-height: 1;
    }

    .total-label {
      font-size: 12px;
      color: var(--text-muted);
    }
  }

  .stock-basic-meta {
    display: flex;
    gap: 12px;
    font-size: 11px;
    color: var(--text-secondary);

    .meta-item {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .meta-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      display: inline-block;

      &.valid {
        background: var(--down);
      }

      &.st {
        background: #f5a623;
      }

      &.delisted {
        background: var(--up);
      }

      &.concept {
        background: var(--accent);
      }

      &.etf {
        background: #9b59b6;
      }
    }
  }

  .market-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .market-row {
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

  .last-sync {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    padding-top: 8px;
    border-top: 1px solid var(--rule);
  }

  .last-sync-extra {
    font-size: 11px;
    color: var(--text-muted);
  }

  .last-sync-extra-row {
    font-size: 11px;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    padding-top: 4px;
  }
}

.btn-sync-small {
  padding: 4px 10px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

.btn-missing {
  background: var(--text-secondary);
}

.missing-tag {
  margin-left: 4px;
  color: var(--text-secondary);
  font-size: 10px;
}

.col-incremental {
  text-align: center;
}

.toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);

  input[type="checkbox"] {
    cursor: pointer;
  }
}

.daily-section {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.daily-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  .section-title {
    margin-bottom: 0;
  }
}

.section-note {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.action-btns {
  display: flex;
  gap: 6px;
}

.section-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-primary);
  margin: 0 0 12px;
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

@media (max-width: 1200px) {
  .top-section {
    grid-template-columns: 1fr;
  }
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

/* Pipeline */
.pipeline-section {
  display: flex;
  flex-direction: column;
}

.pipeline-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.pipeline-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pipeline-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}

.pipeline-card-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-primary);
}

.pipeline-card-desc {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.pipeline-steps-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pipeline-date-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}

.pipeline-date-input {
  flex: 1;
  padding: 6px 8px;
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  outline: none;

  &:focus {
    border-color: var(--accent);
  }
}

.step-tag {
  font-size: 10px;
  padding: 2px 8px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: 2px;
  font-family: var(--font-mono);
}

.btn-pipeline-start {
  padding: 8px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.btn-pipeline-start:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-pipeline-cancel {
  padding: 4px 12px;
  background: var(--up);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
}

.pipeline-status-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pipeline-status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pipeline-status-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;
}

.pipeline-status-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 2px;
  font-weight: 600;
}

.pipeline-status-badge.status-running {
  background: var(--accent-subtle);
  color: var(--accent);
}

.pipeline-status-badge.status-success {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.pipeline-status-badge.status-failed {
  background: rgba(244, 67, 54, 0.15);
  color: #f44336;
}

.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pipeline-step {
  display: grid;
  grid-template-columns: 28px 1fr 28px;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-size: 12px;
}

.pipeline-step.step-running {
  border-color: var(--accent);
}

.pipeline-step.step-success {
  border-color: rgba(76, 175, 80, 0.4);
}

.pipeline-step.step-failed {
  border-color: rgba(244, 67, 54, 0.4);
}

.step-index {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border-radius: 50%;
  font-size: 10px;
  font-family: var(--font-mono);
  font-weight: 600;
}

.step-name {
  color: var(--text-secondary);
}

.step-status-icon {
  text-align: center;
  font-size: 14px;
}

.icon-success {
  color: #4caf50;
}

.icon-failed {
  color: #f44336;
}

.icon-running .spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--accent-subtle);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.step-error {
  grid-column: 1 / -1;
  font-size: 11px;
  color: #f44336;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .pipeline-cards {
    grid-template-columns: 1fr;
  }
}

</style>
