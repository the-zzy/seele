<script setup>
import { reactive, watch, ref } from 'vue'
import { toast } from '@/composables/useToast'

const props = defineProps({
  visible: { type: Boolean, default: false },
  positions: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:visible', 'submit'])

const form = reactive({
  symbol: '',
  name: '',
  trade_date: '',
  buy_price: '',
  sell_price: '',
  quantity: ''
})

const showDropdown = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
let searchTimer = null

watch(() => props.visible, (val) => {
  if (val) {
    form.symbol = ''
    form.name = ''
    form.trade_date = new Date().toISOString().slice(0, 10)
    form.buy_price = ''
    form.sell_price = ''
    form.quantity = ''
    closeDropdown()
  }
})

function openDropdown () {
  showDropdown.value = true
  searchKeyword.value = ''
  searchResults.value = props.positions
}

function closeDropdown () {
  showDropdown.value = false
  searchKeyword.value = ''
  searchResults.value = []
  if (searchTimer) clearTimeout(searchTimer)
}

function onSearchInput () {
  const kw = searchKeyword.value.trim()
  if (!kw) {
    searchResults.value = props.positions
    return
  }
  const lower = kw.toLowerCase()
  searchResults.value = props.positions.filter(p =>
    p.symbol.toLowerCase().includes(lower) ||
    p.name.toLowerCase().includes(lower)
  )
}

function onSelectStock (item) {
  form.symbol = item.symbol
  form.name = item.name
  if (item.quantity != null) {
    form.quantity = String(item.quantity)
  }
  closeDropdown()
}

function onClose () {
  emit('update:visible', false)
}

function onSubmit () {
  if (!form.symbol.trim()) {
    toast.warning('请选择股票')
    return
  }
  if (!form.trade_date) {
    toast.warning('请选择交易日期')
    return
  }
  const buyPrice = Number(form.buy_price)
  if (!buyPrice || buyPrice <= 0) {
    toast.warning('请输入有效的买入价格')
    return
  }
  const sellPrice = Number(form.sell_price)
  if (!sellPrice || sellPrice <= 0) {
    toast.warning('请输入有效的卖出价格')
    return
  }
  const qty = Number(form.quantity)
  if (!qty || qty <= 0 || !Number.isInteger(qty) || qty % 100 !== 0) {
    toast.warning('请输入有效的成交股数（100股的整数倍）')
    return
  }

  emit('submit', {
    symbol: form.symbol.trim(),
    name: form.name.trim(),
    trade_date: form.trade_date,
    buy_price: buyPrice,
    sell_price: sellPrice,
    quantity: qty
  })
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="onClose">
    <div class="modal-panel">
      <div class="modal-header">
        <h3 class="modal-title">录入做T</h3>
        <button class="modal-close" @click="onClose">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <label>股票</label>
          <div class="stock-select">
            <div
              class="select-trigger"
              :class="{ active: showDropdown }"
              @click="openDropdown"
            >
              <span v-if="form.symbol" class="trigger-value">
                {{ form.symbol }} {{ form.name }}
              </span>
              <span v-else class="trigger-placeholder">请选择持仓股票</span>
              <span class="trigger-arrow">&#9662;</span>
            </div>
            <div v-if="showDropdown" class="select-dropdown">
              <div class="dropdown-search">
                <input
                  v-model="searchKeyword"
                  placeholder="输入代码或名称搜索"
                  type="text"
                  @input="onSearchInput"
                  @click.stop
                >
              </div>
              <div class="dropdown-list">
                <div
                  v-for="item in searchResults"
                  :key="item.symbol"
                  class="dropdown-item"
                  :class="{ selected: form.symbol === item.symbol }"
                  @click="onSelectStock(item)"
                >
                  <span class="symbol">{{ item.symbol }}</span>
                  <span class="name">{{ item.name }}</span>
                  <span class="meta">{{ item.quantity }}股 / 成本{{ Number(item.avg_cost).toFixed(2) }}</span>
                </div>
                <div v-if="!searchResults.length" class="dropdown-empty">
                  无持仓
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label>交易日期</label>
          <input v-model="form.trade_date" type="date">
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label>买入价格</label>
            <input v-model="form.buy_price" placeholder="元" type="number" step="0.01">
          </div>
          <div class="form-row">
            <label>卖出价格</label>
            <input v-model="form.sell_price" placeholder="元" type="number" step="0.01">
          </div>
        </div>
        <div class="form-row">
          <label>成交股数</label>
          <input v-model="form.quantity" placeholder="100股的整数倍" type="number" step="100">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-link" @click="onClose">取消</button>
        <button class="btn-primary daytrade" @click="onSubmit">确认做T</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 10px;
  width: 460px;
  min-height: 360px;
  max-width: 96vw;
  max-height: 96vh;
  box-shadow: var(--shadow-soft);
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--rule);
}

.modal-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;

  &:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }
}

.modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  overflow: auto;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  input {
    padding: 8px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 6px;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;

    &:focus {
      border-color: var(--border-focus);
    }
  }
}

.stock-select {
  position: relative;
}

.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s;

  &:hover,
  &.active {
    border-color: var(--border-focus);
  }
}

.trigger-value {
  color: var(--text-primary);
}

.trigger-placeholder {
  color: var(--text-muted);
}

.trigger-arrow {
  color: var(--text-muted);
  font-size: 11px;
  margin-left: 8px;
}

.select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  box-shadow: var(--shadow-soft);
  z-index: 10;
  display: flex;
  flex-direction: column;
  max-height: 360px;
}

.dropdown-search {
  padding: 8px;
  border-bottom: 1px solid var(--rule);

  input {
    width: 100%;
    box-sizing: border-box;
    padding: 6px 8px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 4px;
    font-size: 12px;
    outline: none;

    &:focus {
      border-color: var(--border-focus);
    }
  }
}

.dropdown-list {
  overflow: auto;
  flex: 1;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 12px;
  border-bottom: 1px solid var(--rule);

  &:last-child {
    border-bottom: none;
  }

  &:hover,
  &.selected {
    background: var(--bg-tertiary);
  }

  .symbol {
    font-family: var(--font-mono);
    color: var(--text-primary);
    min-width: 80px;
  }

  .name {
    color: var(--text-secondary);
    flex: 1;
  }

  .meta {
    color: var(--text-muted);
    font-size: 11px;
  }
}

.dropdown-empty {
  padding: 12px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--rule);
}

.btn-link {
  padding: 7px 14px;
  background: transparent;
  color: var(--text-muted);
  border: none;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
}

.btn-primary {
  padding: 7px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: #fff;
  background: var(--accent);

  &:hover {
    background: var(--accent-hover);
  }

  &.daytrade {
    background: #8b5cf6;

    &:hover {
      background: #7c3aed;
    }
  }
}

@media (max-width: 768px) {
  .modal-panel {
    width: 100%;
    border-radius: 12px 12px 0 0;
    max-height: calc(92vh - var(--safe-bottom));
    padding-bottom: var(--safe-bottom);
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .modal-footer {
    flex-direction: column;

    button {
      width: 100%;
      min-height: var(--touch-target);
    }
  }

  .select-dropdown {
    max-height: 240px;
  }
}
</style>
