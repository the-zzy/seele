<script setup>
import { computed } from 'vue'
import { useViewport } from '@/composables/useViewport'

const props = defineProps({
  pageNum: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true }
})

const emit = defineEmits(['update:pageNum', 'update:pageSize'])

const { isMobile } = useViewport()

const totalPages = computed(() => Math.ceil(props.total / props.pageSize) || 1)

function prev () {
  if (props.pageNum > 1) {
    emit('update:pageNum', props.pageNum - 1)
  }
}

function next () {
  if (props.pageNum < totalPages.value) {
    emit('update:pageNum', props.pageNum + 1)
  }
}

function onSizeChange (e) {
  emit('update:pageSize', Number(e.target.value))
  emit('update:pageNum', 1)
}
</script>

<template>
  <div class="pagination">
    <div class="pg-meta">
      <span class="pg-label">Page</span>
      <span class="pg-num">{{ String(pageNum).padStart(2, '0') }}</span>
      <span class="pg-sep">/</span>
      <span class="pg-total">{{ String(totalPages).padStart(2, '0') }}</span>
      <span class="pg-count">· {{ total.toLocaleString() }} 条</span>
    </div>

    <div class="pg-controls">
      <button :disabled="pageNum <= 1" class="btn-page" @click="prev">← 上一页</button>
      <button :disabled="pageNum >= totalPages" class="btn-page" @click="next">下一页 →</button>
    </div>

    <div v-if="!isMobile" class="pg-size">
      <span class="pg-label">Size</span>
      <select :value="pageSize" @change="onSizeChange">
        <option :value="10">10</option>
        <option :value="20">20</option>
        <option :value="50">50</option>
        <option :value="100">100</option>
      </select>
    </div>
  </div>
</template>

<style scoped lang="scss">
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  flex-shrink: 0;
}

.pg-meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);

  .pg-label {
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
    margin-right: 4px;
  }

  .pg-num {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 14px;
  }

  .pg-sep {
    opacity: 0.4;
    color: var(--text-faint);
  }

  .pg-total {
    color: var(--text-secondary);
  }

  .pg-count {
    color: var(--text-muted);
    margin-left: 4px;
  }
}

.pg-controls {
  display: flex;
  gap: 8px;
}

.btn-page {
  padding: 6px 14px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    border-color: var(--text-faint);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
}

.pg-size {
  display: flex;
  align-items: center;
  gap: 8px;

  .pg-label {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  select {
    padding: 5px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--rule);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    cursor: pointer;
    transition: border-color 0.2s;

    &:hover, &:focus {
      border-color: var(--text-faint);
    }
  }
}

@media (max-width: 768px) {
  .pagination {
    gap: 10px;
    padding: 12px 0;
  }

  .pg-controls {
    flex: 1;

    .btn-page {
      flex: 1;
      min-height: var(--touch-target);
      padding: 8px 10px;
    }
  }
}
</style>
