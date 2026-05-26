<template>
  <div class="agent-chat" :class="{ 'chat-widget': mode === 'widget', 'chat-page': mode === 'page' }">
    <div class="chat-header">
      <div class="chat-title">
        <span class="chat-icon">◈</span>
        <span>Seele AI Agent</span>
      </div>
      <div class="chat-actions">
        <label v-if="mode === 'page'" class="write-toggle" title="开启后 Agent 可执行写入操作">
          <input v-model="allowWrite" type="checkbox">
          <span>允许写入</span>
        </label>
        <button class="action-btn" title="清空会话" @click="onClear">清空</button>
        <slot name="extra-actions" />
      </div>
    </div>

    <div ref="messagesRef" class="chat-messages">
      <div v-if="!messages.length" class="chat-welcome">
        <div class="welcome-icon">◈</div>
        <div class="welcome-title">Seele AI Agent</div>
        <div class="welcome-desc">
          你可以向我询问股票数据、财务指标、持仓分析，<br>
          也可以让我帮你录入交易、修改持仓设置。
        </div>
        <div class="welcome-hints">
          <button v-for="hint in hints" :key="hint" class="hint-chip" @click="sendHint(hint)">
            {{ hint }}
          </button>
        </div>
      </div>

      <AgentMessage
        v-for="(msg, idx) in messages"
        :key="idx"
        :role="msg.role"
        :content="msg.content"
        :tool-calls="msg.toolCalls"
      />

      <div v-if="showLoading" class="chat-loading">
        <span class="loading-dot" />
        <span class="loading-dot" />
        <span class="loading-dot" />
      </div>
    </div>

    <div v-if="mode === 'widget'" class="chat-write-bar">
      <label class="write-toggle">
        <input v-model="allowWrite" type="checkbox">
        <span>允许写入</span>
      </label>
    </div>

    <AgentInput :loading="loading" @send="onSend" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { useAgent } from '@/composables/useAgent'
import AgentMessage from './AgentMessage.vue'
import AgentInput from './AgentInput.vue'

const props = defineProps({
  mode: { type: String, default: 'widget' }
})

const { messages, loading, sendMessage, clearSession } = useAgent()
const messagesRef = ref(null)
const allowWrite = ref(false)

const showLoading = computed(() => {
  if (!loading.value) return false
  const last = messages.value[messages.value.length - 1]
  if (!last || last.role !== 'assistant') return true
  return !last.content && !(last.toolCalls && last.toolCalls.length)
})

const hints = [
  '查询我的持仓',
  '分析 600519 的财务指标',
  '今天市场情绪如何？',
  '运行主升浪选股',
  '查询最近 5 天的盈亏'
]

function onSend (text) {
  sendMessage(text, allowWrite.value)
}

function sendHint (text) {
  sendMessage(text, allowWrite.value)
}

function onClear () {
  clearSession()
}

function scrollToBottom () {
  const el = messagesRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

watch(messages, () => {
  nextTick(scrollToBottom)
}, { deep: true })

watch(loading, () => {
  nextTick(scrollToBottom)
})
</script>

<style lang="scss" scoped>
.agent-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  overflow: hidden;
}

.chat-widget {
  max-height: 600px;
}

.chat-page {
  border-radius: 0;
  border: none;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;

  .chat-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-display);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);

    .chat-icon {
      color: var(--accent);
      font-size: 16px;
    }
  }

  .chat-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .action-btn {
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 4px 10px;
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

.write-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;

  input[type="checkbox"] {
    accent-color: var(--accent);
  }
}

.chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 16px;
}

.chat-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  text-align: center;
  gap: 12px;

  .welcome-icon {
    font-size: 32px;
    color: var(--accent);
    opacity: 0.6;
  }

  .welcome-title {
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .welcome-desc {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
  }

  .welcome-hints {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    margin-top: 8px;

    .hint-chip {
      background: var(--bg-secondary);
      border: 1px solid var(--rule);
      border-radius: 16px;
      padding: 6px 14px;
      font-size: 12px;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        border-color: var(--accent);
        color: var(--accent);
      }
    }
  }
}

.chat-loading {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 0;

  .loading-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-faint);
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-write-bar {
  padding: 6px 16px 0;
  display: flex;
  justify-content: flex-end;
}
</style>
