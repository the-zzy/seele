<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true }
})

const emit = defineEmits(['update:modelValue', 'search', 'reset'])

const form = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

function onSearch () {
  emit('search')
}

function onReset () {
  emit('reset')
}
</script>

<template>
  <div class="filter-section">
    <label class="field">
      <span class="field-label">代码</span>
      <input v-model="form.symbol" type="text" placeholder="600519" @keyup.enter="onSearch" />
    </label>
    <label class="field">
      <span class="field-label">名称</span>
      <input v-model="form.name" type="text" placeholder="输入名称" @keyup.enter="onSearch" />
    </label>
    <label class="field">
      <span class="field-label">交易日</span>
      <input v-model="form.tradeDate" type="date" @change="onSearch" />
    </label>
    <label class="field">
      <span class="field-label">市值≥(亿)</span>
      <input v-model.number="form.floatMarketCapMin" type="number" placeholder="200" @keyup.enter="onSearch" />
    </label>
    <label class="field">
      <span class="field-label">股价≤(元)</span>
      <input v-model.number="form.closeMax" type="number" placeholder="300" @keyup.enter="onSearch" />
    </label>
    <label class="field">
      <span class="field-label">换手≥(%)</span>
      <input v-model.number="form.avgTurnoverMin" type="number" placeholder="2" @keyup.enter="onSearch" />
    </label>
    <label class="field">
      <span class="field-label">成交额≥(亿)</span>
      <input v-model.number="form.avgAmountMin" type="number" placeholder="2" @keyup.enter="onSearch" />
    </label>
    <label class="field checkbox-field">
      <span class="field-label">均线多头</span>
      <input v-model="form.maBull" type="checkbox" @change="onSearch" />
    </label>
    <div class="filter-actions">
      <button class="btn-link" @click="onReset">重置</button>
      <button class="btn-primary" @click="onSearch">检索</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.filter-section {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px 12px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  margin-bottom: 12px;
}

.field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  &.checkbox-field {
    gap: 6px;
    cursor: pointer;

    input[type='checkbox'] {
      width: 14px;
      height: 14px;
      accent-color: var(--accent);
      cursor: pointer;
    }

    .field-label {
      width: auto;
    }
  }

  .field-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
    width: auto;
    text-align: right;
  }

  input {
    flex: 1;
    width: 0;
    padding: 7px 12px;
    background: var(--bg-input);
    border: 1px solid var(--rule);
    border-radius: 6px;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-primary);
    transition: border-color 0.2s;
    min-width: 0;

    &:focus {
      outline: none;
      border-color: var(--border-focus);
    }

    &::placeholder {
      color: var(--text-muted);
    }
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  grid-column: span 2;
}

.btn-primary {
  padding: 7px 16px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  transition: background 0.2s;

  &:hover { background: var(--accent-hover); }
}

.btn-link {
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  padding: 7px 12px;
  border-radius: 6px;
  transition: all 0.2s;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
}
</style>
