<script setup>
defineProps({
  section: { type: String, default: '' },
  number: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  meta: { type: String, default: '' }
})
</script>

<template>
  <header class="page-hero">
    <div class="hero-left">
      <div class="hero-meta">
        <span v-if="number" class="hero-num">{{ number }}</span>
        <span v-if="number && section" class="hero-sep">/</span>
        <span v-if="section" class="hero-section">{{ section }}</span>
        <span v-if="meta" class="hero-extra">· {{ meta }}</span>
      </div>
      <h1 class="hero-title">{{ title }}</h1>
      <p v-if="description" class="hero-desc">{{ description }}</p>
    </div>
    <div class="hero-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped lang="scss">
.page-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 16px 0 10px;
  margin: 0 0 10px;
  border-bottom: 1px solid var(--rule);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    bottom: -1px;
    width: 56px;
    height: 1px;
    background: var(--accent);
  }

  @media (max-width: 900px) {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 18px 0 14px;
  }
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);

  .hero-num {
    color: var(--accent);
    font-weight: 600;
  }

  .hero-section {
    color: var(--text-secondary);
  }

  .hero-extra {
    color: var(--text-muted);
  }

  .hero-sep {
    opacity: 0.5;
  }
}

.hero-title {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 24px;
  line-height: 1.2;
  letter-spacing: -0.01em;
  color: var(--text-primary);
}

.hero-desc {
  margin: 4px 0 0;
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;

  @media (max-width: 900px) {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .page-hero {
    gap: 12px;
  }

  .hero-title {
    font-size: 20px;
  }

  .hero-desc {
    white-space: normal;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .hero-actions {
    gap: 8px;

    > * {
      min-height: var(--touch-target);
    }
  }
}
</style>
