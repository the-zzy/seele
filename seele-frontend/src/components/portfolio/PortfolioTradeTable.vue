<script setup>
import { computed } from 'vue'
import { useViewport } from '@/composables/useViewport'
import { useFixedRows } from '@/composables/useFixedRows'
import MobileCardList from '@/components/common/MobileCardList.vue'

const props = defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  sortField: { type: String, default: 'trade_date' },
  sortOrder: { type: String, default: 'desc' }
})

const emit = defineEmits(['delete', 'edit', 'sort'])

const { isMobile } = useViewport()

function onSort (field) {
  emit('sort', field)
}

function getSortIcon (field) {
  if (field !== props.sortField) return '⇅'
  return props.sortOrder === 'asc' ? '▲' : '▼'
}

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function onEdit (item) {
  emit('edit', item)
}

function isDayTrade (item) {
  return item.remark && item.remark.includes('[做T]')
}

function typeLabel (item) {
  if (isDayTrade(item)) return '做T'
  return item.trade_type === 'BUY' ? '买入' : '卖出'
}

function onDelete (item) {
  if (confirm(`确定删除该笔 ${typeLabel(item)} 记录？`)) {
    emit('delete', item.id)
  }
}

const sortedList = computed(() => {
  const field = props.sortField
  const order = props.sortOrder
  const multiplier = order === 'desc' ? -1 : 1

  return [...props.list].sort((a, b) => {
    const va = a[field]
    const vb = b[field]

    if (va == null && vb == null) return 0
    if (va == null) return 1 * multiplier
    if (vb == null) return -1 * multiplier

    if (typeof va === 'number' && typeof vb === 'number') {
      return (va - vb) * multiplier
    }

    return String(va).localeCompare(String(vb), 'zh-CN') * multiplier
  })
})

const paddedList = useFixedRows(sortedList)

function typeClass (item) {
  if (isDayTrade(item)) return 'daytrade'
  return item.trade_type.toLowerCase()
}
</script>

<template>
  <div class="table-section">
    <div class="section-title">
      交易记录
      <span v-if="list.length" class="section-count">{{ list.length }} 笔</span>
    </div>
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="!list.length" class="state empty">暂无记录</div>
    <MobileCardList
      v-else-if="isMobile"
      :list="list"
      key-field="id"
    >
      <template #default="{ item }">
        <div class="trade-card">
          <div class="card-header">
            <div class="header-left">
              <span class="card-symbol">{{ item.symbol }}</span>
              <span class="tag" :class="typeClass(item)">{{ typeLabel(item) }}</span>
            </div>
            <span class="card-name">{{ item.name }}</span>
            <span class="card-date">{{ item.trade_date }}</span>
          </div>
          <div class="card-fields">
            <div class="card-field">
              <span class="field-label">价格</span>
              <span class="field-value">{{ fmt(item.price) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">股数</span>
              <span class="field-value">{{ item.quantity != null ? item.quantity.toLocaleString() : '-' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">金额</span>
              <span class="field-value">{{ fmt(item.amount) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">印花税</span>
              <span class="field-value">{{ fmt(item.stamp_tax) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">过户费</span>
              <span class="field-value">{{ fmt(item.transfer_fee) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">合计费用</span>
              <span class="field-value">{{ fmt(item.total_fee) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-edit" @click.stop="onEdit(item)">编辑</button>
            <button class="btn-del" @click.stop="onDelete(item)">删除</button>
          </div>
        </div>
      </template>
    </MobileCardList>
    <div v-else class="table-wrap">
      <table class="stock-table">
        <thead>
          <tr>
            <th class="sortable" @click="onSort('trade_date')"><span class="th-label">日期</span><span class="sort-icon">{{ getSortIcon('trade_date') }}</span></th>
            <th class="sortable" @click="onSort('trade_type')"><span class="th-label">类型</span><span class="sort-icon">{{ getSortIcon('trade_type') }}</span></th>
            <th class="sortable" @click="onSort('symbol')"><span class="th-label">股票代码</span><span class="sort-icon">{{ getSortIcon('symbol') }}</span></th>
            <th class="sortable" @click="onSort('name')"><span class="th-label">股票名称</span><span class="sort-icon">{{ getSortIcon('name') }}</span></th>
            <th class="sortable num" @click="onSort('price')"><span class="th-label">价格</span><span class="sort-icon">{{ getSortIcon('price') }}</span></th>
            <th class="sortable num" @click="onSort('quantity')"><span class="th-label">股数</span><span class="sort-icon">{{ getSortIcon('quantity') }}</span></th>
            <th class="sortable num" @click="onSort('amount')"><span class="th-label">金额</span><span class="sort-icon">{{ getSortIcon('amount') }}</span></th>
            <th class="sortable num" @click="onSort('stamp_tax')"><span class="th-label">印花税</span><span class="sort-icon">{{ getSortIcon('stamp_tax') }}</span></th>
            <th class="sortable num" @click="onSort('transfer_fee')"><span class="th-label">过户费</span><span class="sort-icon">{{ getSortIcon('transfer_fee') }}</span></th>
            <th class="sortable num" @click="onSort('total_fee')"><span class="th-label">合计费用</span><span class="sort-icon">{{ getSortIcon('total_fee') }}</span></th>
            <th class="act">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, index) in paddedList"
            :key="item === null ? `empty-${index}` : (item.id || item.symbol || index)"
            class="data-row"
            :class="{ 'empty-row': item === null }"
          >
            <template v-if="item">
              <td class="mono">{{ item.trade_date }}</td>
              <td>
                <span
                  class="tag"
                  :class="typeClass(item)"
                >
                  {{ typeLabel(item) }}
                </span>
              </td>
              <td class="mono">{{ item.symbol }}</td>
              <td>{{ item.name }}</td>
              <td class="num">{{ fmt(item.price) }}</td>
              <td class="num">{{ item.quantity != null ? item.quantity.toLocaleString() : '-' }}</td>
              <td class="num">{{ fmt(item.amount) }}</td>
              <td class="num">{{ fmt(item.stamp_tax) }}</td>
              <td class="num">{{ fmt(item.transfer_fee) }}</td>
              <td class="num">{{ fmt(item.total_fee) }}</td>
              <td class="act">
                <button class="btn-edit" @click="onEdit(item)">编辑</button>
                <button class="btn-del" @click="onDelete(item)">删除</button>
              </td>
            </template>
            <template v-else>
              <td v-for="col in ['date','type','symbol','name','price','quantity','amount','stamp_tax','transfer_fee','total_fee','act']" :key="col">&nbsp;</td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-wrap {
  overflow: auto;
}

.stock-table {
  min-width: 980px;

  th.sortable {
    cursor: pointer;
    user-select: none;

    &:hover {
      color: var(--text-primary);
    }
  }

  .th-label {
    margin-right: 4px;
  }

  .sort-icon {
    font-size: 10px;
    color: var(--text-muted);
  }
}

.num {
  text-align: right;
}

.act {
  text-align: center;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;

  &.buy {
    background: rgba(239, 68, 68, 0.12);
    color: var(--up);
  }

  &.sell {
    background: rgba(59, 130, 246, 0.12);
    color: var(--accent);
  }

  &.daytrade {
    background: rgba(168, 85, 247, 0.12);
    color: #a855f7;
  }
}

.btn-edit,
.btn-del {
  padding: 4px 10px;
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  color: var(--text-muted);
  background: transparent;

  &:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
}

.btn-del {
  &:hover {
    border-color: var(--up);
    color: var(--up);
  }
}

.trade-card {
  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--rule);
    flex-wrap: wrap;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .card-symbol {
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

  .card-date {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
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

  .card-actions {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>
