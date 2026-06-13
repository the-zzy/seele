<script setup>
import { ref } from 'vue'
import { useViewport } from '@/composables/useViewport'
import MobileCardList from '@/components/common/MobileCardList.vue'

defineProps({
  list: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['edit', 'update-position'])

const { isMobile } = useViewport()

const pnlMode = ref('history') // 'history' | 'current'
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
    <div class="pnl-toggle">
      <span class="pnl-toggle-label">盈亏显示</span>
      <button
        class="pnl-toggle-btn"
        :class="{ active: pnlMode === 'history' }"
        @click="pnlMode = 'history'"
      >
        历史盈亏
      </button>
      <button
        class="pnl-toggle-btn"
        :class="{ active: pnlMode === 'current' }"
        @click="pnlMode = 'current'"
      >
        当前盈亏
      </button>
    </div>
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="!list.length" class="state empty">暂无持仓</div>
    <MobileCardList
      v-else-if="isMobile"
      :list="list"
      key-field="symbol"
    >
      <template #default="{ item }">
        <div class="position-card" :class="alertClass(item)">
          <div class="card-header">
            <div class="header-left">
              <span class="card-symbol">{{ item.symbol }}</span>
              <span v-if="alertText(item)" class="alert-badge">{{ alertText(item) }}</span>
            </div>
            <span class="card-name">{{ item.name }}</span>
            <span class="group-tag" :class="item.group">{{ item.group || 'default' }}</span>
          </div>
          <div class="card-fields">
            <div class="card-field">
              <span class="field-label">持仓股数</span>
              <span class="field-value">{{ item.quantity != null ? item.quantity.toLocaleString() : '-' }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">平均成本</span>
              <span class="field-value">{{ fmt(item.avg_cost) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">最新价</span>
              <span class="field-value">{{ fmt(item.current_price) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">市值</span>
              <span class="field-value">{{ fmt(item.market_value) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">{{ pnlMode === 'history' ? '历史盈亏' : '当前盈亏' }}</span>
              <span
                class="field-value"
                :class="pnlClass(pnlMode === 'history' ? item.history_pnl : item.unrealized_pnl)"
              >{{ fmt(pnlMode === 'history' ? item.history_pnl : item.unrealized_pnl) }}</span>
            </div>
            <div class="card-field">
              <span class="field-label">盈亏比例</span>
              <span
                class="field-value"
                :class="pnlClass(pnlMode === 'history' ? item.history_pnl_pct : item.unrealized_pnl_pct)"
              >{{ fmt(pnlMode === 'history' ? item.history_pnl_pct : item.unrealized_pnl_pct) }}%</span>
            </div>
            <div class="card-field">
              <span class="field-label">持仓天数</span>
              <span class="field-value">{{ holdingDays(item.first_buy_date) }}</span>
            </div>
            <div class="card-field wide">
              <span class="field-label">备注</span>
              <span class="field-value remark">{{ item.remark || '-' }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-edit" @click.stop="startEdit(item)">编辑</button>
          </div>
        </div>
        <div v-if="editingSymbol === item.symbol" class="mobile-edit-form">
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
          <div class="edit-field wide">
            <label>备注</label>
            <input v-model="editForm.remark" placeholder="备注" type="text">
          </div>
          <div class="edit-actions">
            <button class="btn-link" @click="cancelEdit">取消</button>
            <button class="btn-primary" @click="saveEdit(item.symbol)">保存</button>
          </div>
        </div>
      </template>
    </MobileCardList>
    <div v-else class="table-wrap">
      <table class="stock-table">
        <thead>
          <tr>
            <th>股票代码</th>
            <th>股票名称</th>
            <th class="num">持仓股数</th>
            <th class="num">平均成本</th>
            <th class="num">最新价</th>
            <th class="num">市值</th>
            <th class="num">{{ pnlMode === 'history' ? '历史盈亏' : '当前盈亏' }}</th>
            <th class="num">盈亏比例</th>
            <th>持仓天数</th>
            <th>分组</th>
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in list" :key="item.symbol">
            <td class="mono">
              {{ item.symbol }}
              <span v-if="alertText(item)" class="alert-badge">{{ alertText(item) }}</span>
            </td>
            <td>{{ item.name }}</td>
            <td class="num">{{ item.quantity != null ? item.quantity.toLocaleString() : '-' }}</td>
            <td class="num">{{ fmt(item.avg_cost) }}</td>
            <td class="num">{{ fmt(item.current_price) }}</td>
            <td class="num">{{ fmt(item.market_value) }}</td>
            <td
              class="num"
              :class="pnlClass(pnlMode === 'history' ? item.history_pnl : item.unrealized_pnl)"
            >
              {{ fmt(pnlMode === 'history' ? item.history_pnl : item.unrealized_pnl) }}
            </td>
            <td
              class="num"
              :class="pnlClass(pnlMode === 'history' ? item.history_pnl_pct : item.unrealized_pnl_pct)"
            >
              {{ fmt(pnlMode === 'history' ? item.history_pnl_pct : item.unrealized_pnl_pct) }}%
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
          <tr v-if="editingSymbol" class="edit-row">
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
                  <button class="btn-primary" @click="saveEdit(editingSymbol)">保存</button>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.pnl-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.pnl-toggle-label {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
}

.pnl-toggle-btn {
  padding: 3px 10px;
  border: 1px solid var(--rule);
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  color: var(--text-muted);
  background: transparent;
  transition: all 0.2s;

  &.active {
    color: #fff;
    background: var(--accent);
    border-color: var(--accent);
  }

  &:hover:not(.active) {
    border-color: var(--accent);
    color: var(--accent);
  }
}

.table-wrap {
  overflow: auto;
}

.stock-table {
  min-width: 960px;
}

.num {
  text-align: right;
}

.alert-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: var(--up);
}

.alert-stop-loss {
  background: rgba(239, 68, 68, 0.06);
}

.alert-take-profit {
  background: rgba(16, 185, 129, 0.06);
}

.warning {
  background: rgba(234, 179, 8, 0.06);
}

.profit {
  background: rgba(59, 130, 246, 0.06);
}

.group-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;

  &.default {
    background: var(--bg-tertiary);
    color: var(--text-muted);
  }

  &.core {
    background: rgba(59, 130, 246, 0.12);
    color: var(--accent);
  }

  &.watch {
    background: rgba(234, 179, 8, 0.12);
    color: #eab308;
  }

  &.trial {
    background: rgba(168, 85, 247, 0.12);
    color: #a855f7;
  }
}

.remark {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edit-row {
  background: var(--bg-tertiary);

  td {
    padding: 12px 14px;
  }
}

.edit-form {
  display: flex;
  align-items: center;
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

  input,
  select {
    padding: 6px 8px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 4px;
    font-size: 12px;
    outline: none;
    width: 110px;

    &:focus {
      border-color: var(--accent);
    }
  }
}

.edit-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.btn-edit {
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
    background: var(--bg-tertiary);
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

.position-card {
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
  }

  .card-actions {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
  }
}

.mobile-edit-form {
  margin-top: 10px;
  padding: 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;

  .edit-field {
    width: 100%;

    &.wide {
      grid-column: 1 / -1;
    }

    input,
    select {
      width: 100%;
      box-sizing: border-box;
      min-height: var(--touch-target);
    }
  }

  .edit-actions {
    grid-column: 1 / -1;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>
