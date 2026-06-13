<script setup>
import { useViewport } from '@/composables/useViewport'
import MobileCardList from '@/components/common/MobileCardList.vue'

const props = defineProps({
  list: { type: Array, default: () => [] },
  sortField: { type: String, default: 'symbol' },
  sortOrder: { type: String, default: 'asc' },
  loading: Boolean
})

const emit = defineEmits(['sort', 'row-dblclick'])

const { isMobile } = useViewport()

const columns = [
  { key: 'symbol', label: '股票代码', align: 'left' },
  { key: 'name', label: '股票名称', align: 'left' },
  { key: 'industry', label: '所属行业', align: 'left' },
  { key: 'boards', label: '所属板块', align: 'left' },
  { key: 'area', label: '所在地区', align: 'left' },
  { key: 'market', label: '市场板块', align: 'center' },
  { key: 'listDate', label: '上市日期', align: 'center' },
  { key: 'roe', label: 'ROE', align: 'right' },
  { key: 'grossProfitRatio', label: '毛利率', align: 'right' },
  { key: 'netProfitRatio', label: '净利率', align: 'right' },
  { key: 'netProfitYoy', label: '净利润同比', align: 'right' },
  { key: 'revenueYoy', label: '营收同比', align: 'right' }
]

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

function formatDate (val) {
  if (!val) return '-'
  const s = String(val)
  if (s.length === 8) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  }
  return s
}

function formatPercent (val) {
  if (val == null || val === undefined) return '—'
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

function getYoyClass (val) {
  if (val == null) return ''
  return Number(val) >= 0 ? 'up' : 'down'
}

function onRowDblClick (item) {
  emit('row-dblclick', item)
}

function onRowClick (item) {
  emit('row-dblclick', item)
}
</script>

<template>
  <div class="table-section">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">暂无数据</div>
    <MobileCardList
      v-else-if="isMobile"
      :list="list"
      key-field="id"
      @click-item="onRowClick"
    >
      <template #default="{ item }">
        <div class="stock-card">
          <div class="card-header">
            <span class="card-code">{{ extractCodeNum(item.symbol) }}</span>
            <span class="card-name">{{ item.name }}</span>
            <span class="card-market">{{ item.market || '—' }}</span>
          </div>
          <div class="card-fields">
            <div class="card-field">
              <span class="field-label">行业</span>
              <span class="field-value">{{ item.industry || '—' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">ROE</span>
              <span class="field-value">{{ item.roe != null ? `${item.roe.toFixed(2)}%` : '—' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">毛利率</span>
              <span class="field-value">{{ item.grossProfitRatio != null ? `${item.grossProfitRatio.toFixed(2)}%` : '—' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">净利润同比</span>
              <span class="field-value" :class="getYoyClass(item.netProfitYoy)">{{ formatPercent(item.netProfitYoy) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">营收同比</span>
              <span class="field-value" :class="getYoyClass(item.revenueYoy)">{{ formatPercent(item.revenueYoy) }}</span>
            </div>
            <div class="card-field wide">
              <span class="field-label">板块</span>
              <span class="field-value">
                <span v-if="item.boards" class="board-tags">
                  <span
                    v-for="b in item.boards.boards || []"
                    :key="b.code"
                    class="board-tag"
                  >{{ b.name }}</span>
                  <span
                    v-if="item.boards.industry_board"
                    class="board-tag industry"
                  >{{ item.boards.industry_board.name }}</span>
                  <span v-if="!(item.boards.boards?.length) && !item.boards.industry_board">—</span>
                </span>
                <span v-else>—</span>
              </span>
            </div>
          </div>
        </div>
      </template>
    </MobileCardList>
    <table v-else class="stock-table">
      <colgroup>
        <col style="width: 8%">
        <col style="width: 10%">
        <col style="width: 12%">
        <col style="width: 12%">
        <col style="width: 8%">
        <col style="width: 8%">
        <col style="width: 9%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 7%">
        <col style="width: 7%">
      </colgroup>
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="sortable"
            :class="{ 'th-left': col.align === 'left', 'th-center': col.align === 'center' }"
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
          @dblclick="onRowDblClick(item)"
        >
          <td class="code">{{ extractCodeNum(item.symbol) }}</td>
          <td class="name">{{ item.name }}</td>
          <td class="td-left">{{ item.industry || '—' }}</td>
          <td class="td-left">
            <div v-if="item.boards" class="board-tags">
              <span
                v-for="b in item.boards.boards || []"
                :key="b.code"
                class="board-tag"
              >{{ b.name }}</span>
              <span
                v-if="item.boards.industry_board"
                class="board-tag industry"
              >{{ item.boards.industry_board.name }}</span>
              <span v-if="!(item.boards.boards?.length) && !item.boards.industry_board">—</span>
            </div>
            <span v-else>—</span>
          </td>
          <td class="td-left">{{ item.area || '—' }}</td>
          <td class="td-center">{{ item.market || '—' }}</td>
          <td class="td-center">{{ formatDate(item.listDate) }}</td>
          <td>{{ item.roe != null ? `${item.roe.toFixed(2)}%` : '—' }}</td>
          <td>{{ item.grossProfitRatio != null ? `${item.grossProfitRatio.toFixed(2)}%` : '—' }}</td>
          <td>{{ item.netProfitRatio != null ? `${item.netProfitRatio.toFixed(2)}%` : '—' }}</td>
          <td :class="getYoyClass(item.netProfitYoy)">{{ formatPercent(item.netProfitYoy) }}</td>
          <td :class="getYoyClass(item.revenueYoy)">{{ formatPercent(item.revenueYoy) }}</td>
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
  min-width: 1080px;
}

.stock-card {
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

  .card-market {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
    padding: 2px 8px;
    border: 1px solid var(--rule);
    border-radius: 4px;
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

    &.wide {
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
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.board-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.board-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-family: var(--font-mono);
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  white-space: nowrap;

  &.industry {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
}
</style>
