<script setup>
defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['delete', 'edit'])

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function onEdit (item) {
  emit('edit', item)
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
            <th class="num">手续费</th>
            <th class="act">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" class="empty">加载中...</td>
          </tr>
          <tr v-else-if="!list.length">
            <td colspan="9" class="empty">暂无记录</td>
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
            <td class="num">{{ fmt(item.fee) }}</td>
            <td class="act">
              <button class="btn-edit" @click="onEdit(item)">编辑</button>
              <button class="btn-del" @click="onDelete(item)">删除</button>
            </td>
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
</style>
