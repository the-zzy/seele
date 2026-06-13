<template>
  <transition name="fade">
    <div v-if="visible" class="auth-overlay" @click.self="close">
      <div class="auth-modal">
        <div class="auth-masthead">
          <div class="wordmark">Seele</div>
          <div class="meta">选股工作台 · 授权访问</div>
        </div>

        <div class="rule" />

        <form class="auth-form" @submit.prevent="handleLogin">
          <div class="field">
            <label>密码</label>
            <input
              ref="inputRef"
              v-model="password"
              type="password"
              placeholder="输入管理员密码"
              autocomplete="current-password"
              :disabled="loading"
            >
          </div>

          <div v-if="error" class="error-msg">
            {{ error }}
          </div>

          <button
            type="submit"
            class="auth-btn"
            :disabled="loading || !password"
          >
            <span v-if="loading">验证中…</span>
            <span v-else>进入系统</span>
          </button>
        </form>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { setToken } from '@/utils/auth'
import request from '@/utils/request'

const props = defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['update:visible', 'success'])

const password = ref('')
const loading = ref(false)
const error = ref('')
const inputRef = ref(null)

watch(() => props.visible, (v) => {
  if (v) {
    password.value = ''
    error.value = ''
    nextTick(() => inputRef.value?.focus())
  }
})

function close () {
  emit('update:visible', false)
}

async function handleLogin () {
  if (!password.value) return
  loading.value = true
  error.value = ''

  try {
    const data = await request.post('/auth/login', { password: password.value })
    setToken(data.token)
    close()
    emit('success')
  } catch (err) {
    error.value = err.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-modal {
  width: 360px;
  padding: 40px 36px 36px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 10px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4);
}

.auth-masthead {
  text-align: center;
  margin-bottom: 24px;

  .wordmark {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 32px;
    letter-spacing: -0.02em;
    color: var(--text-primary);
  }

  .meta {
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);
  }
}

.rule {
  height: 1px;
  background: var(--rule);
  margin-bottom: 28px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;

  .field {
    display: flex;
    flex-direction: column;
    gap: 8px;

    label {
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-faint);
    }

    input {
      width: 100%;
      box-sizing: border-box;
      background: var(--bg-input);
      color: var(--text-primary);
      border: 1px solid var(--border-default);
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;

      &:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-subtle);
      }

      &::placeholder {
        color: var(--text-muted);
      }
    }
  }

  .error-msg {
    font-size: 12px;
    color: var(--down);
    text-align: center;
  }

  .auth-btn {
    width: 100%;
    padding: 11px;
    margin-top: 4px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;

    &:hover:not(:disabled) {
      opacity: 0.9;
    }

    &:active:not(:disabled) {
      transform: translateY(1px);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .auth-overlay {
    padding: var(--safe-top) 0 var(--safe-bottom);
    align-items: flex-start;
    padding-top: calc(15vh + var(--safe-top));
  }

  .auth-modal {
    width: calc(100% - 32px);
    max-width: 360px;
    padding: 32px 24px 28px;
  }
}
</style>
