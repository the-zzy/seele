<script setup>
import { computed, ref, watch, nextTick, onMounted, toRef } from 'vue'
import { useViewport } from '@/composables/useViewport'
import { useFixedRows } from '@/composables/useFixedRows'
import MobileCardList from '@/components/common/MobileCardList.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import { formatNumber } from '@/utils/formatters'

const props = defineProps({
  list: { type: Array, default: () => [] },
  loading: Boolean
})

const emit = defineEmits(['row-dblclick'])

const { isMobile } = useViewport()

const layers = [20, 10, 5, 'OFF']

function getLayerLabel (layer) {
  if (layer === 'OFF') return 'OFF'
  return `${layer}日`
}

function getLayerDesc (layer) {
  if (layer === 20) return '最近20天≥16天均线多头'
  if (layer === 10) return '最近10天≥7天均线多头'
  if (layer === 5) return '最近5天≥4天均线多头'
  return '均线非多头排列'
}

const groups = computed(() => {
  const grouped = {}
  for (const layer of layers) {
    grouped[layer] = props.list.filter(item => item.layer === layer)
  }
  return grouped
})

const activeLayer = ref(20)
const pageSize = ref(10)
const pageState = ref({
  20: { pageNum: 1 },
  10: { pageNum: 1 },
  5: { pageNum: 1 },
  OFF: { pageNum: 1 }
})

watch(() => props.list, (list) => {
  pageState.value = {
    20: { pageNum: 1 },
    10: { pageNum: 1 },
    5: { pageNum: 1 },
    OFF: { pageNum: 1 }
  }
  if (!list.length) return
  nextTick(() => {
    if (!groups.value[activeLayer.value]?.length) {
      const first = layers.find(l => groups.value[l]?.length > 0)
      if (first) activeLayer.value = first
    }
  })
}, { immediate: false })

const tabRefs = ref([])
const indicatorStyle = ref({ width: '0px', transform: 'translateX(0px)' })

function updateIndicator () {
  const idx = layers.indexOf(activeLayer.value)
  const el = tabRefs.value[idx]
  if (el) {
    indicatorStyle.value = {
      width: `${el.offsetWidth}px`,
      transform: `translateX(${el.offsetLeft}px)`
    }
  }
}

watch(activeLayer, () => {
  if (!pageState.value[activeLayer.value]) {
    pageState.value[activeLayer.value] = { pageNum: 1 }
  }
  nextTick(updateIndicator)
})
onMounted(() => nextTick(updateIndicator))

const currentGroup = computed(() => groups.value[activeLayer.value] || [])

const pageNum = computed(() => pageState.value[activeLayer.value]?.pageNum || 1)

const paginatedGroup = computed(() => {
  const start = (pageNum.value - 1) * pageSize.value
  return currentGroup.value.slice(start, start + pageSize.value)
})

const groupTotal = computed(() => currentGroup.value.length)

const paddedList = useFixedRows(paginatedGroup)

function handlePageChange (newPage) {
  pageState.value[activeLayer.value] = { pageNum: newPage }
}

function handlePageSizeChange (newSize) {
  pageSize.value = newSize
  pageState.value[activeLayer.value] = { pageNum: 1 }
}

function extractCodeNum (symbol) {
  if (!symbol) return ''
  const match = symbol.match(/\d+/)
  return match ? match[0] : symbol
}

function onDblClick (item) {
  emit('row-dblclick', item)
}

function onClick (item) {
  emit('row-dblclick', item)
}

function getScoreClass (score) {
  if (!score || score.total === undefined) return ''
  const total = score.total
  if (total >= 80) return 'score-strong'
  if (total >= 60) return 'score-ok'
  if (total >= 40) return 'score-weak'
  return 'score-poor'
}

function getScoreLabel (score) {
  if (!score || score.total === undefined) return '—'
  const total = score.total
  if (total >= 80) return `${total} 强推`
  if (total >= 60) return `${total} 推荐`
  if (total >= 40) return `${total} 勉强`
  return `${total} 不推荐`
}

function formatDate (dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getChgClass (val) {
  if (val == null) return ''
  const value = parseFloat(val)
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return ''
}

function getPctCellClass (val) {
  if (val == null) return ''
  const value = parseFloat(val)
  if (value > 0) return 'cell-up'
  if (value < 0) return 'cell-down'
  return ''
}

function setTabRef (el, idx) {
  if (el) tabRefs.value[idx] = el
}
</script>

<template>
  <div class="group-section">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">暂无数据</div>
    <template v-else>
      <!-- 横线滑块 Tab -->
      <div class="tab-slider">
        <div class="tab-list">
          <div
            v-for="(layer, idx) in layers"
            :key="layer"
            class="tab-item"
            :class="{ active: activeLayer === layer, empty: !groups[layer]?.length }"
            @click="groups[layer]?.length ? activeLayer = layer : null"
            :ref="el => setTabRef(el, idx)"
          >
            <div class="tab-main">
              <span class="tab-label">{{ getLayerLabel(layer) }}</span>
              <span class="tab-count">{{ groups[layer]?.length || 0 }}</span>
            </div>
            <div class="tab-desc">{{ getLayerDesc(layer) }}</div>
          </div>
          <div class="tab-indicator" :style="indicatorStyle"></div>
        </div>
      </div>

      <!-- 当前分组内容 -->
      <div class="table-section">
        <div v-if="!currentGroup.length" class="state empty">该分组暂无数据</div>
        <MobileCardList
          v-else-if="isMobile"
          :list="paginatedGroup"
          key-field="symbol"
          @click-item="onClick"
        >
          <template #default="{ item }">
            <div class="stock-card" :class="{ holding: item.isHolding }">
              <div class="card-header">
                <span class="card-code">{{ extractCodeNum(item.symbol) }}</span>
                <span class="card-name">{{ item.name }}</span>
                <span v-if="item.industry" class="card-industry">{{ item.industry }}</span>
                <span class="score-tag" :class="getScoreClass(item.score)">{{ getScoreLabel(item.score) }}</span>
              </div>
              <div class="card-fields">
                <div class="card-field">
                  <span class="field-label">股价</span>
                  <span class="field-value">{{ item.close != null ? formatNumber(item.close) : '-' }}</span>
                </div>
                <div class="card-field">
                  <span class="field-label">涨幅</span>
                  <span class="field-value" :class="getChgClass(item.pctChg)">{{ item.pctChg != null ? (item.pctChg > 0 ? '+' : '') + item.pctChg.toFixed(2) + '%' : '-' }}</span>
                </div>
                <div class="card-field">
                  <span class="field-label">MA5 / MA10 / MA20</span>
                  <span class="field-value">
                    {{ item.ma5 != null ? formatNumber(item.ma5) : '-' }} /
                    {{ item.ma10 != null ? formatNumber(item.ma10) : '-' }} /
                    {{ item.ma20 != null ? formatNumber(item.ma20) : '-' }}
                  </span>
                </div>
                <div class="card-field">
                  <span class="field-label">启动日</span>
                  <span class="field-value">{{ formatDate(item.launchDate) }}</span>
                </div>
                <div class="card-field">
                  <span class="field-label">启动至今</span>
                  <span class="field-value" :class="getChgClass(item.launchPctChg)">{{ item.launchPctChg != null ? (item.launchPctChg > 0 ? '+' : '') + item.launchPctChg.toFixed(2) + '%' : '-' }}</span>
                </div>
              </div>
            </div>
          </template>
        </MobileCardList>
        <table v-else class="stock-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>板块</th>
              <th>评分</th>
              <th>股价</th>
              <th>涨幅</th>
              <th>MA5</th>
              <th>MA10</th>
              <th>MA20</th>
              <th>启动日</th>
              <th>启动至今</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in paddedList"
              :key="item === null ? `empty-${index}` : (item.id || item.symbol || index)"
              class="data-row"
              :class="{ holding: item?.isHolding, 'empty-row': item === null }"
              @dblclick="item && onDblClick(item)"
            >
              <template v-if="item">
                <td class="code">{{ extractCodeNum(item.symbol) }}</td>
                <td class="name">{{ item.name }}</td>
                <td class="industry">{{ item.industry || '-' }}</td>
                <td :class="getScoreClass(item.score)">
                  {{ getScoreLabel(item.score) }}
                </td>
                <td>{{ item.close != null ? formatNumber(item.close) : '-' }}</td>
                <td class="pct-cell" :class="getPctCellClass(item.pctChg)">
                  {{ item.pctChg != null ? (item.pctChg > 0 ? '+' : '') + item.pctChg.toFixed(2) + '%' : '-' }}
                </td>
                <td>{{ item.ma5 != null ? formatNumber(item.ma5) : '-' }}</td>
                <td>{{ item.ma10 != null ? formatNumber(item.ma10) : '-' }}</td>
                <td>{{ item.ma20 != null ? formatNumber(item.ma20) : '-' }}</td>
                <td>{{ formatDate(item.launchDate) }}</td>
                <td class="pct-cell" :class="getPctCellClass(item.launchPctChg)">
                  {{ item.launchPctChg != null ? (item.launchPctChg > 0 ? '+' : '') + item.launchPctChg.toFixed(2) + '%' : '-' }}
                </td>
              </template>
              <template v-else>
                <td v-for="col in ['symbol','name','industry','score','close','pctChg','ma5','ma10','ma20','launchDate','launchPctChg']" :key="col">&nbsp;</td>
              </template>
            </tr>
          </tbody>
        </table>
        <BasePagination
          v-if="groupTotal > 0"
          :page-num="pageNum"
          :page-size="pageSize"
          :total="groupTotal"
          @update:page-num="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.group-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 横线滑块 Tab */
.tab-slider {
  flex-shrink: 0;
  z-index: 10;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--rule);
  padding: 0 16px;
}

.tab-list {
  position: relative;
  display: flex;
  gap: 0;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.tab-item {
  flex-shrink: 0;
  padding: 12px 20px 14px;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
  position: relative;

  &.empty {
    opacity: 0.45;
    cursor: not-allowed;
  }

  &:not(.empty):hover {
    color: var(--text-primary);
  }

  &.active {
    color: var(--accent);
  }
}

.tab-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.tab-label {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
}

.tab-count {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.tab-item.active .tab-count {
  background: var(--accent);
  color: white;
}

.tab-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
}

.tab-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--accent);
  border-radius: 2px 2px 0 0;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.table-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.stock-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 1100px;

  thead,
  tbody {
    display: flex;
    flex-direction: column;
  }

  thead {
    flex-shrink: 0;
  }

  tbody {
    flex: 1;
    overflow-y: auto;
  }

  tr {
    display: flex;
    flex: 0 0 10%;
    min-height: 0;
  }

  th,
  td {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding: 8px 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  th:first-child,
  td:first-child,
  th:nth-child(2),
  td:nth-child(2) {
    justify-content: flex-start;
  }

  th:nth-child(3),
  td:nth-child(3) {
    justify-content: center;
  }
}

.pct-cell {
  justify-content: center;

  &.cell-up { background: var(--up-bg); }
  &.cell-down { background: var(--down-bg); }
}

.stock-table tbody tr:hover {
  .pct-cell.cell-up { background: var(--up-bg-hover); }
  .pct-cell.cell-down { background: var(--down-bg-hover); }
}

.stock-table tbody td.industry {
  justify-content: flex-start;
}

.stock-table .data-row.holding {
  background: rgba(245, 158, 11, 0.08);
}

.stock-table .score-strong { color: var(--up); font-weight: 600; }
.stock-table .score-ok { color: #f59e0b; font-weight: 600; }
.stock-table .score-weak { color: #9ca3af; }
.stock-table .score-poor { color: var(--down); }

@media (max-width: 768px) {
  .tab-list {
    scrollbar-width: auto;

    &::-webkit-scrollbar {
      display: block;
      height: 3px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--text-faint);
      border-radius: 2px;
    }
  }

  .tab-item {
    padding: 10px 14px 12px;
  }

  .tab-desc {
    font-size: 10px;
  }
}

.stock-card {
  &.holding {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.2);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--rule);
  }

  .card-code {
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .card-name {
    flex: 1;
    font-family: var(--font-body);
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-industry {
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    white-space: nowrap;
  }

  .card-fields {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px 16px;
  }

  .card-field {
    display: flex;
    flex-direction: column;
    gap: 4px;

    &:nth-child(3) {
      grid-column: 1 / -1;
    }
  }

  .field-label {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .field-value {
    font-size: 13px;
    color: var(--text-primary);
  }
}
</style>
