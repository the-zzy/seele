<script setup>
defineProps({
  visible: Boolean,
  percent: { type: Number, default: 0 },
  current: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  message: { type: String, default: '' }
})
</script>

<template>
  <transition name="slide-fade">
    <div v-if="visible" class="progress-section">
      <div class="progress-info">
        <span class="info-tag">同步</span>
        <span class="info-msg">{{ message }}</span>
        <span v-if="total > 0" class="info-count">
          <span class="cur">{{ current.toLocaleString() }}</span>
          <span class="sep">/</span>
          <span class="tot">{{ total.toLocaleString() }}</span>
          <span class="pct">{{ percent }}%</span>
        </span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: percent + '%' }" />
      </div>
    </div>
  </transition>
</template>

<style scoped lang="scss">
.progress-section {
  margin: 8px 0 12px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 4px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--accent);
  }
}

.progress-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);

  .info-tag {
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent);
    padding: 2px 8px;
    border-radius: 2px;
    background: var(--accent-subtle);
  }

  .info-msg {
    flex: 1;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .info-count {
    display: inline-flex;
    align-items: baseline;
    gap: 4px;
    font-variant-numeric: tabular-nums;
    color: var(--text-muted);

    .cur { color: var(--text-primary); font-weight: 600; }
    .sep { opacity: 0.4; }
    .tot { color: var(--text-secondary); }
    .pct {
      color: var(--accent);
      margin-left: 8px;
      font-weight: 600;
    }
  }
}

.progress-bar {
  width: 100%;
  height: 3px;
  background: var(--rule);
  overflow: hidden;

  .progress-fill {
    height: 100%;
    background: var(--accent);
    transition: width 0.3s ease;
    background-image: linear-gradient(
      90deg,
      var(--accent) 0%,
      #60a5fa 50%,
      var(--accent) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 2s linear infinite;
  }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
