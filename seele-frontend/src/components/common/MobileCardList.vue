<template>
  <div class="mobile-card-list">
    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="list.length === 0" class="state empty">{{ emptyText }}</div>
    <div v-else class="card-list">
      <div
        v-for="item in list"
        :key="keyExtractor(item)"
        class="mobile-card"
        @click="onClick(item)"
      >
        <slot :item="item" />
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  list: { type: Array, default: () => [] },
  loading: Boolean,
  emptyText: { type: String, default: '暂无数据' },
  keyField: { type: String, default: 'id' }
})

const emit = defineEmits(['click-item'])

function keyExtractor (item) {
  return item[props.keyField] ?? item.symbol ?? item.code ?? JSON.stringify(item)
}

function onClick (item) {
  emit('click-item', item)
}
</script>

<style scoped lang="scss">
.mobile-card-list {
  height: 100%;
  overflow-y: auto;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 0;
}

.mobile-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:active {
    background: var(--bg-tertiary);
    border-color: var(--border-default);
  }
}

.state {
  text-align: center;
  padding: 60px 20px;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-faint);
}
</style>
