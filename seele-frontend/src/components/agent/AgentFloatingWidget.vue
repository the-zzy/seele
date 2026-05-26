<template>
  <div class="agent-widget">
    <!-- 悬浮按钮 -->
    <button
      v-if="!isOpen"
      class="widget-trigger"
      @click="isOpen = true"
    >
      <span class="trigger-icon">◈</span>
    </button>

    <!-- 聊天面板 -->
    <div v-else class="widget-panel">
      <AgentChat mode="widget">
        <template #extra-actions>
          <button class="action-btn expand-btn" title="展开全屏" @click="goToPage">
            ⛶
          </button>
          <button class="action-btn close-btn" title="关闭" @click="isOpen = false">
            ✕
          </button>
        </template>
      </AgentChat>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AgentChat from './AgentChat.vue'

const router = useRouter()
const isOpen = ref(false)

function goToPage () {
  router.push('/agent')
  isOpen.value = false
}
</script>

<style lang="scss" scoped>
.agent-widget {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1000;
}

.widget-trigger {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
  }

  .trigger-icon {
    font-size: 22px;
    line-height: 1;
  }
}

.widget-panel {
  width: 400px;
  height: 560px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border-radius: 10px;
  overflow: hidden;

  .action-btn {
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: var(--text-faint);
      color: var(--text-primary);
    }
  }
}
</style>
