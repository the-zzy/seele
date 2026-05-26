<template>
  <div class="agent-input">
    <textarea
      v-model="text"
      rows="1"
      placeholder="输入问题，例如：查询我的持仓、分析 600519..."
      @keydown.enter.prevent="onEnter"
      @input="autoResize"
      ref="textareaRef"
    />
    <button
      class="send-btn"
      :disabled="!canSend"
      @click="send"
    >
      发送
    </button>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['send'])

const text = ref('')
const textareaRef = ref(null)

const canSend = computed(() => text.value.trim() && !props.loading)

function send () {
  const t = text.value.trim()
  if (!t || props.loading) return
  emit('send', t)
  text.value = ''
  nextTick(() => autoResize())
}

function onEnter () {
  send()
}

function autoResize () {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}
</script>

<style lang="scss" scoped>
.agent-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--rule);
  background: var(--bg-primary);

  textarea {
    flex: 1;
    min-height: 36px;
    max-height: 120px;
    padding: 8px 12px;
    border: 1px solid var(--rule);
    border-radius: 6px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-family: var(--font-body);
    font-size: 13px;
    line-height: 1.5;
    resize: none;
    outline: none;

    &:focus {
      border-color: var(--accent);
    }

    &::placeholder {
      color: var(--text-faint);
    }
  }

  .send-btn {
    height: 36px;
    padding: 0 16px;
    border: none;
    border-radius: 6px;
    background: var(--accent);
    color: #fff;
    font-family: var(--font-display);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s;
    flex-shrink: 0;

    &:hover:not(:disabled) {
      opacity: 0.9;
    }

    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }
}
</style>
