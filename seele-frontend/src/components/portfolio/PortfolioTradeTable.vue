<script setup>
defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['delete'])

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function onDelete (item) {
  if (confirm(`确定删除该笔 ${item.trade_type === 'BUY' ? '买入' : '卖出'} 记录？`)) {
    emit('delete', item.id)
  }
}
</script>

<template>
  <div class="table-section">
    <div class="section-title">
      交易记录
      <span v-if="list.length" class="section-count">{{ list.length }} 笔</span>
    </div>
    <div class="table-wrap">
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
            <th class="act">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="empty">加载中...</td>
          </tr>
          <tr v-else-if="!list.length">
            <td colspan="8" class="empty">暂无记录</td>
          </tr>
          <tr v-for="item in list" :key="item.id">
            <td class="mono">{{ item.trade_date }}</td>
            <td>
              <span class="tag" :class="item.trade_type.toLowerCase()">
                {{ item.trade_type === 'BUY' ? '买入' : '卖出' }}
              </span>
            </td>
            <td class="mono">{{ item.symbol }}</td>
            <td>{{ item.name }}</td>
            <td class="num">{{ fmt(item.price) }}</td>
            <td class="num">{{ item.quantity != null ? item.quantity.toLocaleString() : '-' }}</td>
            <td class="num">{{ fmt(item.amount) }}</td>
            <td class="act">
              <button class="btn-del" @click="onDelete(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.table-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
}

.stock-table {
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
    background: var(--bg-tertiary);
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 500;
    position: sticky;
    top: 0;
    z-index: 1;
  }

  td {
    color: var(--text-secondary);
  }

  tr:hover td {
    background: var(--bg-tertiary);
  }

  .num {
    text-align: right;
    font-family: var(--font-mono);
  }

  .mono {
    font-family: var(--font-mono);
  }

  .act {
    text-align: center;
  }

  .empty {
    text-align: center;
    color: var(--text-muted);
    padding: 28px;
  }
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-mono);

  &.buy {
    background: var(--accent-subtle);
    color: var(--accent);
  }

  &.sell {
    background: rgba(255, 77, 79, 0.12);
    color: var(--up);
  }
}

.btn-del {
  padding: 3px 10px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;

  &:hover {
    color: var(--up);
    border-color: var(--up);
  }
}
</style>
