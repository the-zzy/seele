<script setup>
import { toRef } from 'vue'
import { useViewport } from '@/composables/useViewport'
import { useFixedRows } from '@/composables/useFixedRows'
import MobileCardList from '@/components/common/MobileCardList.vue'

const props = defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['delete', 'edit'])

const { isMobile } = useViewport()

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

const paddedList = useFixedRows(toRef(props, 'list'))

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
              <span class="field-label">手续费</span>
              <span class="field-value">{{ fmt(item.fee) }}</span>
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
            <th>日期</th>
            <th>类型</th>
            <th>股票代码</th>
            <th>股票名称</th>
            <th class="num">价格</th>
            <th class="num">股数</th>
            <th class="num">金额</th>
            <th class="num">手续费</th>
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
              <td class="num">{{ fmt(item.fee) }}</td>
              <td class="act">
                <button class="btn-edit" @click="onEdit(item)">编辑</button>
                <button class="btn-del" @click="onDelete(item)">删除</button>
              </td>
            </template>
            <template v-else>
              <td v-for="col in ['date','type','symbol','name','price','quantity','amount','fee','act']" :key="col">&nbsp;</td>
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
  min-width: 720px;
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
    background: rgba(59, 130, 246, 0.12);
    color: var(--accent);
  }

  &.sell {
    background: rgba(239, 68, 68, 0.12);
    color: var(--up);
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
