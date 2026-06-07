<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '确认操作'
  },
  message: {
    type: String,
    default: ''
  },
  detail: {
    type: String,
    default: ''
  },
  confirmText: {
    type: String,
    default: '确认'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="visible" class="confirm-layer" @click.self="emit('cancel')">
        <section class="confirm-card" role="dialog" aria-modal="true" :aria-label="title">
          <div class="confirm-orb" aria-hidden="true">
            <span></span>
          </div>

          <div class="confirm-copy">
            <p class="eyebrow">同步确认</p>
            <h2>{{ title }}</h2>
            <p class="message">{{ message }}</p>
            <p v-if="detail" class="detail">{{ detail }}</p>
          </div>

          <div class="confirm-actions">
            <button class="btn ghost" type="button" :disabled="loading" @click="emit('cancel')">
              {{ cancelText }}
            </button>
            <button class="btn primary" type="button" :disabled="loading" @click="emit('confirm')">
              <span class="dot"></span>
              {{ loading ? '处理中...' : confirmText }}
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
.confirm-layer {
  position: fixed;
  inset: 0;
  z-index: 4000;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 50% 35%, rgba(59, 130, 246, 0.16), transparent 32%),
    rgba(10, 15, 25, 0.34);
  backdrop-filter: blur(8px);
}

.confirm-card {
  position: relative;
  width: min(460px, calc(100vw - 40px));
  overflow: hidden;
  padding: 28px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: 24px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.94)),
    var(--bg-secondary);
  box-shadow:
    0 24px 70px rgba(15, 23, 42, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  animation: confirm-pop 0.22s ease-out;
}

html[data-theme='dark'] .confirm-card {
  background:
    linear-gradient(145deg, rgba(31, 41, 55, 0.98), rgba(17, 24, 39, 0.94)),
    var(--bg-secondary);
  box-shadow:
    0 24px 70px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.confirm-orb {
  position: absolute;
  top: -54px;
  right: -46px;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(16, 185, 129, 0.16));
}

.confirm-orb span {
  position: absolute;
  left: 42px;
  bottom: 36px;
  width: 42px;
  height: 42px;
  border-radius: 16px;
  background: var(--accent);
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.34);

  &::before,
  &::after {
    content: '';
    position: absolute;
    background: #fff;
    border-radius: 8px;
  }

  &::before {
    left: 12px;
    top: 20px;
    width: 8px;
    height: 2px;
    transform: rotate(42deg);
  }

  &::after {
    left: 17px;
    top: 18px;
    width: 16px;
    height: 2px;
    transform: rotate(-45deg);
  }
}

.confirm-copy {
  position: relative;
  padding-right: 72px;
}

.eyebrow {
  margin: 0 0 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--accent);
  text-transform: uppercase;
}

h2 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 22px;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.message {
  margin: 14px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.detail {
  margin: 16px 0 0;
  padding: 12px 14px;
  border: 1px solid var(--rule);
  border-radius: 14px;
  background: var(--accent-subtle);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 26px;
}

.btn {
  height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.16s, box-shadow 0.16s, background 0.16s;

  &:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }

  &:not(:disabled):hover {
    transform: translateY(-1px);
  }
}

.ghost {
  border: 1px solid var(--border-default);
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--accent), var(--accent-hover));
  color: #fff;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.28);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.18);
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.18s ease;
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

@keyframes confirm-pop {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 560px) {
  .confirm-card {
    padding: 24px;
    border-radius: 20px;
  }

  .confirm-copy {
    padding-right: 48px;
  }

  h2 {
    font-size: 20px;
  }

  .confirm-actions {
    flex-direction: column-reverse;
  }

  .btn {
    width: 100%;
  }
}
</style>
