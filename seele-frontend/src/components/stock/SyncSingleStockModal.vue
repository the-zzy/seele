<script setup>
import { reactive, ref, watch } from 'vue'
import { stockBasicApi } from '@/api/stock'
import { toast } from '@/composables/useToast'

const props = defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['update:visible', 'submit'])

const form = reactive({
  symbol: '',
  name: '',
  tradeDate: ''
})

const showDropdown = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
let searchTimer = null

watch(() => props.visible, (val) => {
  if (val) {
    form.symbol = ''
    form.name = ''
    form.tradeDate = new Date().toISOString().slice(0, 10)
    closeDropdown()
  }
})

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
  closeDropdown()
}

function onClose () {
  emit('update:visible', false)
}

function onSubmit () {
  if (!form.symbol) {
    toast.warning('请选择股票')
    return
  }
  if (!form.tradeDate) {
    toast.warning('请选择交易日期')
    return
  }
  emit('submit', {
    symbol: form.symbol,
    trade_date: form.tradeDate
  })
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="onClose">
    <div class="modal-panel">
      <div class="modal-header">
        <h3 class="modal-title">同步单股数据</h3>
        <button class="modal-close" @click="onClose">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <label>股票</label>
          <div class="stock-select">
            <div
              class="select-trigger"
              :class="{ active: showDropdown }"
              @click="showDropdown ? closeDropdown() : (loadDefaultList(), showDropdown = true)"
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
                <div v-if="!searchResults.length" class="dropdown-empty">
                  {{ searchLoading ? '搜索中...' : '无结果' }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label>交易日期</label>
          <input v-model="form.tradeDate" type="date">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-link" @click="onClose">取消</button>
        <button class="btn-primary" @click="onSubmit">开始同步</button>
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
  gap: 14px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  input {
    padding: 8px 10px;
    border: 1px solid var(--rule);
    border-radius: 6px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 13px;

    &:focus {
      outline: none;
      border-color: var(--accent);
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
  border: 1px solid var(--rule);
  border-radius: 6px;
  background: var(--bg-primary);
  cursor: pointer;
  min-height: 36px;

  &.active {
    border-color: var(--accent);
  }
}

.trigger-value {
  color: var(--text-primary);
  font-size: 13px;
}

.trigger-placeholder {
  color: var(--text-muted);
  font-size: 13px;
}

.trigger-arrow {
  color: var(--text-muted);
  font-size: 10px;
}

.select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  box-shadow: var(--shadow-soft);
  z-index: 1100;
  max-height: 280px;
  display: flex;
  flex-direction: column;
}

.dropdown-search {
  padding: 10px;
  border-bottom: 1px solid var(--rule);

  input {
    width: 100%;
    box-sizing: border-box;
  }
}

.dropdown-list {
  overflow-y: auto;
  padding: 6px;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;

  &:hover,
  &.selected {
    background: var(--accent-subtle);
  }

  .symbol {
    color: var(--text-primary);
    font-weight: 500;
    min-width: 64px;
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
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid var(--rule);
}

.btn-link {
  padding: 7px 14px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;

  &:hover {
    color: var(--text-primary);
  }
}

.btn-primary {
  padding: 7px 16px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;

  &:hover {
    background: var(--accent-hover);
  }
}
</style>
