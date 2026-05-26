<script setup>
import { reactive, watch, ref } from 'vue'
import { stockBasicApi } from '@/api/stock'
import { toast } from '@/composables/useToast'

const props = defineProps({
  visible: { type: Boolean, default: false },
  type: { type: String, default: 'BUY' }, // BUY / SELL
  positions: { type: Array, default: () => [] },
  editData: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'submit'])

const form = reactive({
  symbol: '',
  name: '',
  trade_date: '',
  price: '',
  quantity: '',
  fee: '',
  realizedPnl: '',
  remark: ''
})

const showDropdown = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
let searchTimer = null

watch(() => props.visible, (val) => {
  if (val) {
    if (props.editData) {
      // 编辑模式：预填充数据
      form.symbol = props.editData.symbol || ''
      form.name = props.editData.name || ''
      form.trade_date = props.editData.trade_date || ''
      form.price = props.editData.price != null ? String(props.editData.price) : ''
      form.quantity = props.editData.quantity != null ? String(props.editData.quantity) : ''
      form.fee = props.editData.fee != null ? String(props.editData.fee) : ''
      form.realizedPnl = ''
      form.remark = props.editData.remark || ''
    } else {
      // 新增模式：清空表单
      form.symbol = ''
      form.name = ''
      form.trade_date = new Date().toISOString().slice(0, 10)
      form.price = ''
      form.quantity = ''
      form.fee = ''
      form.realizedPnl = ''
      form.remark = ''
    }
    closeDropdown()
  }
})

function openDropdown () {
  showDropdown.value = true
  searchKeyword.value = ''
  if (props.type === 'SELL') {
    searchResults.value = props.positions
  } else {
    loadDefaultList()
  }
}

function closeDropdown () {
  showDropdown.value = false
  searchKeyword.value = ''
  searchResults.value = []
  if (searchTimer) clearTimeout(searchTimer)
}

async function loadDefaultList () {
  searchLoading.value = true
  try {
    const res = await stockBasicApi.pageQuery({
      page_num: 1,
      page_size: 50,
      sort_field: 'symbol',
      sort_order: 'asc'
    })
    searchResults.value = res?.list || []
  } catch (e) {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

function onSearchInput () {
  const kw = searchKeyword.value.trim()
  if (props.type === 'SELL') {
    // 本地过滤持仓
    if (!kw) {
      searchResults.value = props.positions
    } else {
      const lower = kw.toLowerCase()
      searchResults.value = props.positions.filter(p =>
        p.symbol.toLowerCase().includes(lower) ||
        p.name.toLowerCase().includes(lower)
      )
    }
    return
  }
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => doSearch(kw), 300)
}

async function doSearch (kw) {
  searchLoading.value = true
  try {
    const res = await stockBasicApi.pageQuery({
      page_num: 1,
      page_size: 50,
      symbol: kw,
      name: kw,
      sort_field: 'symbol',
      sort_order: 'asc'
    })
    searchResults.value = res?.list || []
  } catch (e) {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

function onSelectStock (item) {
  form.symbol = item.symbol
  form.name = item.name
  if (props.type === 'SELL' && item.quantity != null) {
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
  const price = Number(form.price)
  if (!price || price <= 0) {
    toast.warning('请输入有效的成交价格')
    return
  }
  const qty = Number(form.quantity)
  if (!qty || qty <= 0 || !Number.isInteger(qty) || qty % 100 !== 0) {
    toast.warning('请输入有效的成交股数（100股的整数倍）')
    return
  }
  const data = {
    symbol: form.symbol.trim(),
    name: form.name.trim(),
    trade_type: props.type,
    trade_date: form.trade_date,
    price: price,
    quantity: qty
  }
  if (form.fee !== '' && form.fee != null) {
    data.fee = Number(form.fee)
  }
  if (props.type === 'SELL' && form.realizedPnl !== '' && form.realizedPnl != null) {
    data.realized_pnl = Number(form.realizedPnl)
  }
  if (form.remark) data.remark = form.remark.trim()
  if (props.editData) {
    data.id = props.editData.id
  }
  emit('submit', data)
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="onClose">
    <div class="modal-panel">
      <div class="modal-header">
        <h3 class="modal-title">{{ props.editData ? '编辑交易' : (type === 'BUY' ? '录入买入' : '录入卖出') }}</h3>
        <button class="modal-close" @click="onClose">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <label>股票</label>
          <div v-if="props.editData" class="stock-display">
            {{ form.symbol }} {{ form.name }}
          </div>
          <div v-else class="stock-select">
            <div
              class="select-trigger"
              :class="{ active: showDropdown }"
              @click="openDropdown"
            >
              <span v-if="form.symbol" class="trigger-value">
                {{ form.symbol }} {{ form.name }}
              </span>
              <span v-else class="trigger-placeholder">请选择股票</span>
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
                <template v-if="type === 'SELL'">
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
                </template>
                <template v-else>
                  <div
                    v-for="item in searchResults"
                    :key="item.symbol"
                    class="dropdown-item"
                    :class="{ selected: form.symbol === item.symbol }"
                    @click="onSelectStock(item)"
                  >
                    <span class="symbol">{{ item.symbol }}</span>
                    <span class="name">{{ item.name }}</span>
                    <span class="meta">{{ item.industry }}</span>
                  </div>
                </template>
                <div v-if="!searchResults.length" class="dropdown-empty">
                  {{ searchLoading ? '搜索中...' : '无结果' }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label>交易日期</label>
          <input v-model="form.trade_date" type="date">
        </div>
        <div class="form-row">
          <label>成交价格</label>
          <input v-model="form.price" placeholder="元" type="number" step="0.01">
        </div>
        <div class="form-row">
          <label>成交股数</label>
          <input v-model="form.quantity" placeholder="100股的整数倍" type="number" step="100">
        </div>
        <div v-if="props.editData && type === 'SELL'" class="form-row">
          <label>盈亏金额</label>
          <input v-model="form.realizedPnl" placeholder="元（重新填写以重新计算手续费）" type="number" step="0.01">
        </div>
        <div v-if="!props.editData && type === 'SELL'" class="form-row">
          <label>盈亏金额</label>
          <input v-model="form.realizedPnl" placeholder="元（用于自动计算手续费）" type="number" step="0.01">
        </div>
        <div class="form-row">
          <label>手续费</label>
          <input v-model="form.fee" placeholder="元（可选）" type="number" step="0.01">
        </div>
        <div class="form-row">
          <label>备注</label>
          <input v-model="form.remark" placeholder="可选" type="text">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-link" @click="onClose">取消</button>
        <button class="btn-primary" :class="type.toLowerCase()" @click="onSubmit">
          {{ type === 'BUY' ? '确认买入' : '确认卖出' }}
        </button>
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
  width: 50vw;
  height: 50vh;
  min-width: 400px;
  min-height: 400px;
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

.stock-display {
  padding: 8px 10px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  font-size: 13px;
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

  &.sell {
    background: var(--up);

    &:hover {
      background: #e04345;
    }
  }
}
</style>
