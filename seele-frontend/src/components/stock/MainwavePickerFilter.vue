<script setup>
const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  showSymbol: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue', 'search', 'reset'])

function updateField (key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

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
      <span class="field-label">名称</span>
      <input
        :value="modelValue.name"
        @input="updateField('name', $event.target.value)"
        type="text"
        placeholder="输入名称"
        @keyup.enter="onSearch"
      />
    </label>
    <label class="field">
      <span class="field-label">交易日</span>
      <input
        :value="modelValue.tradeDate"
        @change="updateField('tradeDate', $event.target.value); onSearch()"
        type="date"
      />
    </label>
    <label class="field">
      <span class="field-label">市值≥(亿)</span>
      <input
        :value="modelValue.floatMarketCapMin"
        @input="updateField('floatMarketCapMin', Number($event.target.value))"
        type="number"
        placeholder="200"
        @keyup.enter="onSearch"
      />
    </label>
    <label class="field">
      <span class="field-label">股价≤(元)</span>
      <input
        :value="modelValue.closeMax"
        @input="updateField('closeMax', Number($event.target.value))"
        type="number"
        placeholder="300"
        @keyup.enter="onSearch"
      />
    </label>
    <label class="field">
      <span class="field-label">换手≥(%)</span>
      <input
        :value="modelValue.avgTurnoverMin"
        @input="updateField('avgTurnoverMin', Number($event.target.value))"
        type="number"
        placeholder="2"
        @keyup.enter="onSearch"
      />
    </label>
    <label class="field">
      <span class="field-label">成交额≥(亿)</span>
      <input
        :value="modelValue.avgAmountMin"
        @input="updateField('avgAmountMin', Number($event.target.value))"
        type="number"
        placeholder="2"
        @keyup.enter="onSearch"
      />
    </label>
    <label class="field checkbox-field">
      <span class="field-label">均线多头</span>
      <input
        :checked="modelValue.maBull"
        @change="updateField('maBull', $event.target.checked); onSearch()"
        type="checkbox"
      />
    </label>
    <div class="filter-actions">
      <button class="btn-link" @click="onReset">重置</button>
      <button class="btn-primary" @click="onSearch">检索</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.filter-section {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 8px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  margin-bottom: 10px;
}

.field {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1 1 140px;

  &.checkbox-field {
    gap: 6px;
    cursor: pointer;
    flex: 0 0 auto;

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
    font-size: 11px;
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
    padding: 5px 10px;
    background: var(--bg-input);
    border: 1px solid var(--rule);
    border-radius: 5px;
    font-family: var(--font-mono);
    font-size: 12px;
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
  gap: 8px;
  flex: 0 0 auto;
  margin-left: auto;
}

.btn-primary {
  padding: 5px 14px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
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
  font-size: 11px;
  color: var(--text-muted);
  padding: 5px 10px;
  border-radius: 5px;
  transition: all 0.2s;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
}

@media (max-width: 768px) {
  .filter-section {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .field {
    flex-direction: column;
    align-items: stretch;
    gap: 5px;
    flex: 1 1 auto;

    .field-label {
      width: auto;
      text-align: left;
    }

    input {
      width: 100%;
      box-sizing: border-box;
    }
  }

  .filter-actions {
    justify-content: stretch;
    width: 100%;
    margin-left: 0;

    button {
      flex: 1;
      min-height: var(--touch-target);
    }
  }
}
</style>
