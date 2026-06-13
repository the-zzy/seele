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
  gap: 12px;
  padding: 8px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 6px;
  margin-bottom: 10px;
}

.filter-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  flex: 1;
}

.field {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 140px;
  flex: 1;

  .field-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
    width: 28px;
    text-align: right;
  }

  input {
    flex: 1;
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
  gap: 8px;
  flex-shrink: 0;
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
    min-width: auto;

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

    button {
      flex: 1;
      min-height: var(--touch-target);
    }
  }
}
</style>
