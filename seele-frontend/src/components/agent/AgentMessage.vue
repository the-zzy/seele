<template>
  <div class="agent-message" :class="roleClass">
    <div class="message-avatar">
      <span v-if="role === 'user'">我</span>
      <span v-else-if="role === 'assistant'">AI</span>
      <span v-else>!</span>
    </div>
    <div class="message-body">
      <div class="message-content" :class="{ 'thinking-pulse': isThinking }" v-html="renderedContent" />
      <div v-if="toolCalls && toolCalls.length" class="message-tools">
        <AgentToolCall
          v-for="(tc, idx) in toolCalls"
          :key="idx"
          :name="tc.name"
          :args="tc.arguments"
          :result="tc.result"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AgentToolCall from './AgentToolCall.vue'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  toolCalls: { type: Array, default: () => [] }
})

const roleClass = computed(() => `msg-${props.role}`)
const isThinking = computed(() => props.role === 'assistant' && props.content && props.content.startsWith('正在分析'))

function simpleMarkdown (text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // code blocks
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => {
    return `<pre><code>${code.trim()}</code></pre>`
  })

  // inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  // bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // unordered list
  html = html.replace(/(^|\n)([-*])\s+(.+)/g, '$1<li>$3</li>')
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')

  // paragraphs (split by double newline)
  const blocks = html.split(/\n\n+/)
  html = blocks.map(b => {
    if (b.startsWith('<pre>') || b.startsWith('<ul>')) return b
    return `<p>${b.replace(/\n/g, '<br>')}</p>`
  }).join('')

  return html
}

const renderedContent = computed(() => simpleMarkdown(props.content))
</script>

<style lang="scss" scoped>
.agent-message {
  display: flex;
  gap: 10px;
  padding: 10px 0;

  .message-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .message-body {
    flex: 1;
    min-width: 0;
  }

  .message-content {
    font-size: 13px;
    line-height: 1.6;
    word-break: break-word;

    :deep(p) {
      margin: 0 0 8px;
      &:last-child { margin-bottom: 0; }
    }

    :deep(code) {
      background: var(--bg-secondary);
      padding: 1px 4px;
      border-radius: 3px;
      font-family: var(--font-mono);
      font-size: 12px;
    }

    :deep(pre) {
      background: var(--bg-secondary);
      padding: 10px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 12px;
      line-height: 1.5;
      margin: 4px 0;
    }

    :deep(pre code) {
      background: transparent;
      padding: 0;
    }

    :deep(ul) {
      margin: 4px 0;
      padding-left: 18px;
    }

    :deep(li) {
      margin: 2px 0;
    }

    :deep(strong) {
      font-weight: 600;
    }
  }

  .message-tools {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
}

.msg-user {
  .message-avatar {
    background: var(--accent-subtle);
    color: var(--accent);
  }

  .message-content {
    color: var(--text-primary);
  }
}

.msg-assistant {
  .message-avatar {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border: 1px solid var(--rule);
  }

  .message-content {
    color: var(--text-secondary);
  }
}

.msg-error {
  .message-avatar {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  .message-content {
    color: #ef4444;
  }
}

.thinking-pulse {
  animation: thinking-breathe 2s ease-in-out infinite;
  color: var(--text-faint) !important;
}

@keyframes thinking-breathe {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
</style>
