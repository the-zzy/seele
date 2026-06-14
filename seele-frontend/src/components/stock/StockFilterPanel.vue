<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  showFetch: { type: Boolean, default: false },
  fetching: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'search', 'reset', 'fetch'])

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

function onFetch () {
  emit('fetch')
}
</script>

<template>
  <div class="filter-section">
    <div class="filter-fields">
      <label class="field">
        <span class="field-label">交易日</span>
        <input v-model="form.tradeDate" type="date" @change="onSearch" />
      </label>

      <label class="field">
        <span class="field-label">代码</span>
        <input v-model="form.symbol" type="text" placeholder="600519 / 茅台" @keyup.enter="onSearch" />
      </label>

      <div class="field exclude-field">
        <span class="field-label">板块过滤</span>
        <div class="exclude-chips">
          <label><input v-model="form.excludeSt" type="checkbox" @change="onSearch" /><span>排除 ST</span></label>
          <label><input v-model="form.excludeCyb" type="checkbox" @change="onSearch" /><span>排除创业板</span></label>
          <label><input v-model="form.excludeKcb" type="checkbox" @change="onSearch" /><span>排除科创板</span></label>
          <label><input v-model="form.excludeBse" type="checkbox" @change="onSearch" /><span>排除北交所</span></label>
        </div>
      </div>
    </div>

    <div class="filter-actions">
      <button class="btn-link" @click="onReset">重置</button>
      <button v-if="showFetch" class="btn-ghost" :disabled="fetching" @click="onFetch">
        <span class="dot" :class="{ pulsing: fetching }" />
        {{ fetching ? '同步中…' : '获取数据' }}
      </button>
      <button class="btn-primary" @click="onSearch">检索</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.filter-section {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 10px 0 12px;
  border-bottom: 1px dashed var(--rule);
}

.filter-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  flex: 1;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .field-label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  > input {
    padding: 5px 0;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--rule);
    border-radius: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-primary);
    transition: border-color 0.2s;
    min-width: 140px;

    &:focus {
      outline: none;
      border-bottom-color: var(--accent);
    }

    &::placeholder {
      color: var(--text-faint);
    }
  }
}

.exclude-field {
  flex: 1;
  min-width: 260px;
}

.exclude-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 2px;

  label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    border: 1px solid var(--rule);
    border-radius: 999px;
    cursor: pointer;
    font-size: 11px;
    color: var(--text-muted);
    transition: all 0.18s;
    font-family: var(--font-body);

    &:hover {
      border-color: var(--text-faint);
      color: var(--text-secondary);
    }

    input[type='checkbox'] {
      width: 12px;
      height: 12px;
      margin: 0;
      accent-color: var(--accent);
    }

    &:has(input:checked) {
      background: var(--accent-subtle);
      border-color: rgba(59, 130, 246, 0.35);
      color: var(--text-primary);
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
  padding: 6px 14px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  transition: background 0.2s;

  &:hover { background: var(--accent-hover); }
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  transition: all 0.2s;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--down);

    &.pulsing { animation: pulse 1.2s ease-in-out infinite; }
  }

  &:hover:not(:disabled) {
    border-color: var(--text-faint);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-link {
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 5px 0;
  transition: color 0.2s;

  &:hover { color: var(--text-primary); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

@media (max-width: 768px) {
  .filter-section {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .field {
    width: 100%;

    > input {
      min-width: auto;
      width: 100%;
      box-sizing: border-box;
    }
  }

  .exclude-field {
    min-width: auto;
  }

  .exclude-chips {
    label {
      flex: 1;
      justify-content: center;
      min-height: var(--touch-target);
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
