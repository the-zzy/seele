<script setup>
import { toast } from '@/composables/useToast'

const typeMap = {
  success: { icon: '✓', color: 'var(--down)' },
  error: { icon: '✕', color: 'var(--up)' },
  warning: { icon: '!', color: '#faad14' },
  info: { icon: 'i', color: 'var(--accent)' }
}

function onClose (id) {
  toast.remove(id)
}
</script>

<template>
  <Teleport to="body">
    <TransitionGroup
      tag="div"
      class="toast-container"
      name="toast"
    >
      <div
        v-for="item in toast.list"
        :key="item.id"
        class="toast-item"
        :style="{ '--stripe-color': typeMap[item.type]?.color || typeMap.info.color }"
      >
        <span class="toast-icon">{{ typeMap[item.type]?.icon || typeMap.info.icon }}</span>
        <span class="toast-message">{{ item.message }}</span>
        <button class="toast-close" @click="onClose(item.id)">×</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped lang="scss">
.toast-container {
  position: fixed;
  top: 68px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 200px;
  max-width: 360px;
  padding: 10px 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-left: 3px solid var(--stripe-color);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}

.toast-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--stripe-color);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-close {
  flex-shrink: 0;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.15s;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
}

/* 进入 / 离开动画 */
.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.toast-enter-active {
  transition: all 0.25s ease;
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-move {
  transition: transform 0.2s ease;
}
</style>
