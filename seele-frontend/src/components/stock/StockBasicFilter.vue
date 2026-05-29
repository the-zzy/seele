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
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  margin-bottom: 12px;
}

.filter-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  flex: 1;
}

.field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 160px;
  flex: 1;

  .field-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
    width: 28px;
    text-align: right;
  }

  input {
    flex: 1;
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
  gap: 10px;
  flex-shrink: 0;
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
