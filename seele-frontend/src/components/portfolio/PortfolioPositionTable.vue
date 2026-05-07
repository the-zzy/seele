<script setup>
import { ref } from 'vue'

const props = defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['edit', 'update-position'])

const editingSymbol = ref(null)
const editForm = ref({})

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function pnlClass (v) {
  if (v == null) return ''
  const n = Number(v)
  if (n > 0) return 'up'
  if (n < 0) return 'down'
  return ''
}

function alertClass (item) {
  if (!item.current_price || !item.avg_cost) return ''
  const pnlPct = (item.current_price - item.avg_cost) / item.avg_cost * 100
  if (item.stop_loss_price && item.current_price <= item.stop_loss_price) return 'alert-stop-loss'
  if (item.take_profit_price && item.current_price >= item.take_profit_price) return 'alert-take-profit'
  if (pnlPct <= -5) return 'warning'
  if (pnlPct >= 10) return 'profit'
  return ''
}

function alertText (item) {
  if (!item.current_price || !item.avg_cost) return ''
  if (item.stop_loss_price && item.current_price <= item.stop_loss_price) return '止损'
  if (item.take_profit_price && item.current_price >= item.take_profit_price) return '止盈'
  return ''
}

function startEdit (item) {
  editingSymbol.value = item.symbol
  editForm.value = {
    stop_loss_price: item.stop_loss_price || '',
    take_profit_price: item.take_profit_price || '',
    group: item.group || 'default',
    remark: item.remark || ''
  }
}

function cancelEdit () {
  editingSymbol.value = null
  editForm.value = {}
}

function saveEdit (symbol) {
  const data = {}
  if (editForm.value.stop_loss_price !== '') data.stop_loss_price = Number(editForm.value.stop_loss_price)
  if (editForm.value.take_profit_price !== '') data.take_profit_price = Number(editForm.value.take_profit_price)
  if (editForm.value.group) data.group = editForm.value.group
  if (editForm.value.remark !== '') data.remark = editForm.value.remark
  emit('update-position', symbol, data)
  editingSymbol.value = null
}

function holdingDays (firstBuyDate) {
  if (!firstBuyDate) return '-'
  const days = Math.ceil((new Date() - new Date(firstBuyDate)) / (1000 * 60 * 60 * 24))
  return days + ' 天'
}
</script>

<template>
  <div class="table-section">
    <div class="section-title">
      当前持仓
      <span v-if="list.length" class="section-count">{{ list.length }} 只</span>
    </div>
    <div class="table-wrap">
      <table class="stock-table">
        <thead>
          <tr>
            <th>股票代码</th>
            <th>股票名称</th>
            <th class="num">持仓股数</th>
            <th class="num">平均成本</th>
            <th class="num">最新价</th>
            <th class="num">市值</th>
            <th class="num">浮动盈亏</th>
            <th class="num">盈亏比例</th>
            <th>持仓天数</th>
            <th>分组</th>
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="12" class="empty">加载中...</td>
          </tr>
          <tr v-else-if="!list.length">
            <td colspan="12" class="empty">暂无持仓</td>
          </tr>
          <template v-for="item in list" :key="item.symbol">
            <tr :class="alertClass(item)">
              <td class="mono">
                {{ item.symbol }}
                <span v-if="alertText(item)" class="alert-badge">{{ alertText(item) }}</span>
              </td>
              <td>{{ item.name }}</td>
              <td class="num">{{ item.quantity.toLocaleString() }}</td>
              <td class="num">{{ fmt(item.avg_cost) }}</td>
              <td class="num">{{ fmt(item.current_price) }}</td>
              <td class="num">{{ fmt(item.market_value) }}</td>
              <td class="num" :class="pnlClass(item.unrealized_pnl)">
                {{ fmt(item.unrealized_pnl) }}
              </td>
              <td class="num" :class="pnlClass(item.unrealized_pnl_pct)">
                {{ fmt(item.unrealized_pnl_pct) }}%
              </td>
              <td class="num">{{ holdingDays(item.first_buy_date) }}</td>
              <td>
                <span class="group-tag" :class="item.group">{{ item.group || 'default' }}</span>
              </td>
              <td class="remark">{{ item.remark || '-' }}</td>
              <td>
                <button class="btn-edit" @click="startEdit(item)">编辑</button>
              </td>
            </tr>
            <tr v-if="editingSymbol === item.symbol" class="edit-row">
              <td colspan="12">
                <div class="edit-form">
                  <div class="edit-field">
                    <label>止损价</label>
                    <input v-model="editForm.stop_loss_price" placeholder="元" type="number" step="0.01">
                  </div>
                  <div class="edit-field">
                    <label>止盈价</label>
                    <input v-model="editForm.take_profit_price" placeholder="元" type="number" step="0.01">
                  </div>
                  <div class="edit-field">
                    <label>分组</label>
                    <select v-model="editForm.group">
                      <option value="default">默认</option>
                      <option value="core">核心仓</option>
                      <option value="watch">观察仓</option>
                      <option value="trial">试错仓</option>
                    </select>
                  </div>
                  <div class="edit-field">
                    <label>备注</label>
                    <input v-model="editForm.remark" placeholder="备注" type="text">
                  </div>
                  <div class="edit-actions">
                    <button class="btn-link" @click="cancelEdit">取消</button>
                    <button class="btn-primary" @click="saveEdit(item.symbol)">保存</button>
                  </div>
                </div>
              </td>
            </tr>
          </template>
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

  tr.alert-stop-loss {
    background: rgba(239, 68, 68, 0.06);
  }

  tr.alert-take-profit {
    background: rgba(16, 185, 129, 0.06);
  }

  tr.warning {
    background: rgba(245, 158, 11, 0.04);
  }

  tr.profit {
    background: rgba(16, 185, 129, 0.04);
  }

  .num {
    text-align: right;
    font-family: var(--font-mono);
  }

  .mono {
    font-family: var(--font-mono);
  }

  .up {
    color: var(--up);
  }

  .down {
    color: var(--down);
  }

  .empty {
    text-align: center;
    color: var(--text-muted);
    padding: 28px;
  }

  .alert-badge {
    display: inline-block;
    margin-left: 4px;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    color: #fff;
    background: var(--up);
  }

  .group-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: var(--font-mono);
    background: var(--bg-tertiary);
    color: var(--text-muted);

    &.core {
      background: rgba(59, 130, 246, 0.12);
      color: #3b82f6;
    }

    &.watch {
      background: rgba(245, 158, 11, 0.12);
      color: #f59e0b;
    }

    &.trial {
      background: rgba(139, 92, 246, 0.12);
      color: #8b5cf6;
    }
  }

  .remark {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .btn-edit {
    padding: 3px 10px;
    border: 1px solid var(--rule);
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
    color: var(--text-secondary);
    background: transparent;

    &:hover {
      border-color: var(--accent);
      color: var(--accent);
    }
  }

  .edit-row {
    td {
      padding: 8px 12px;
      background: var(--bg-tertiary);
    }
  }

  .edit-form {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    flex-wrap: wrap;
  }

  .edit-field {
    display: flex;
    flex-direction: column;
    gap: 4px;

    label {
      font-family: var(--font-mono);
      font-size: 9px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-faint);
    }

    input, select {
      padding: 6px 8px;
      background: var(--bg-input);
      color: var(--text-primary);
      border: 1px solid var(--rule);
      border-radius: 4px;
      font-size: 12px;
      outline: none;
      width: 100px;

      &:focus {
        border-color: var(--border-focus);
      }
    }

    input[type="text"] {
      width: 140px;
    }
  }

  .edit-actions {
    display: flex;
    gap: 8px;
    margin-left: auto;
  }

  .btn-link {
    padding: 6px 12px;
    background: transparent;
    color: var(--text-muted);
    border: none;
    font-size: 12px;
    cursor: pointer;
    border-radius: 4px;

    &:hover {
      color: var(--text-primary);
      background: var(--bg-secondary);
    }
  }

  .btn-primary {
    padding: 6px 14px;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    color: #fff;
    background: var(--accent);

    &:hover {
      background: var(--accent-hover);
    }
  }
}
</style>
