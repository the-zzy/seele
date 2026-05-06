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
    <div class="filter-fields">
      <label class="field">
        <span class="field-label">代码</span>
        <input v-model="form.symbol" type="text" placeholder="600519" @keyup.enter="onSearch" />
      </label>
      <label class="field">
        <span class="field-label">名称</span>
        <input v-model="form.name" type="text" placeholder="输入名称" @keyup.enter="onSearch" />
      </label>
      <label class="field">
        <span class="field-label">行业</span>
        <input v-model="form.industry" type="text" placeholder="输入行业" @keyup.enter="onSearch" />
      </label>
      <label class="field">
        <span class="field-label">地区</span>
        <input v-model="form.area" type="text" placeholder="输入地区" @keyup.enter="onSearch" />
      </label>
    </div>

    <div class="filter-actions">
      <button class="btn-link" @click="onReset">重置</button>
      <button class="btn-primary" @click="onSearch">检索</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.filter-section {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 14px 0 16px;
  border-bottom: 1px dashed var(--rule);
}

.filter-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  flex: 1;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 140px;

  .field-label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  input {
    padding: 7px 0;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--rule);
    border-radius: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-primary);
    transition: border-color 0.2s;

    &:focus {
      outline: none;
      border-bottom-color: var(--accent);
    }

    &::placeholder {
      color: var(--text-faint);
    }
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-primary {
  padding: 8px 18px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: background 0.2s;

  &:hover { background: var(--accent-hover); }
}

.btn-link {
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 6px 0;
  transition: color 0.2s;

  &:hover { color: var(--text-primary); }
}
</style>
