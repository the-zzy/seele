<template>
  <div class="gallery-view">
    <div class="gallery-header">
      <h1 class="gallery-title">Seele</h1>
      <span class="gallery-subtitle">希儿官图壁纸 · {{ images.length }} 张</span>
    </div>

    <div v-if="loading" class="state loading">加载中…</div>
    <div v-else-if="images.length === 0" class="state empty">暂无图片</div>
    <div v-else class="masonry">
      <div
        v-for="img in images"
        :key="img"
        class="masonry-item"
        @click="openPreview(img)"
      >
        <img :src="`/gallery/${img}`" :alt="img" loading="lazy">
      </div>
    </div>

    <!-- 预览 -->
    <div v-if="preview" class="preview-overlay" @click.self="closePreview">
      <button class="preview-close" @click="closePreview">✕</button>
      <button v-if="previewIndex > 0" class="preview-nav prev" @click="goPrev">‹</button>
      <button v-if="previewIndex < images.length - 1" class="preview-nav next" @click="goNext">›</button>
      <img :src="`/gallery/${preview}`" class="preview-img" @click.stop>
      <div class="preview-counter">{{ previewIndex + 1 }} / {{ images.length }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const images = ref([])
const loading = ref(true)
const preview = ref(null)

const previewIndex = computed(() => {
  if (!preview.value) return -1
  return images.value.indexOf(preview.value)
})

async function loadImages () {
  try {
    const res = await fetch('/gallery-images.json')
    images.value = await res.json()
  } catch (err) {
    console.error('加载图库失败:', err)
  } finally {
    loading.value = false
  }
}

function openPreview (img) {
  preview.value = img
}

function closePreview () {
  preview.value = null
}

function goPrev () {
  const idx = previewIndex.value
  if (idx > 0) preview.value = images.value[idx - 1]
}

function goNext () {
  const idx = previewIndex.value
  if (idx < images.value.length - 1) preview.value = images.value[idx + 1]
}

function onKeydown (e) {
  if (!preview.value) return
  if (e.key === 'Escape') closePreview()
  if (e.key === 'ArrowLeft') goPrev()
  if (e.key === 'ArrowRight') goNext()
}

onMounted(() => {
  loadImages()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style lang="scss" scoped>
.gallery-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px 28px;
  box-sizing: border-box;
}

.gallery-header {
  margin-bottom: 20px;

  .gallery-title {
    font-family: var(--font-display);
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    letter-spacing: -0.02em;
  }

  .gallery-subtitle {
    display: block;
    margin-top: 6px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-faint);
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }
}

.masonry {
  column-count: 3;
  column-gap: 10px;
}

.masonry-item {
  break-inside: avoid;
  margin-bottom: 10px;
  border-radius: 6px;
  overflow: hidden;
  cursor: zoom-in;
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  transition: transform 0.15s ease, box-shadow 0.15s ease;

  img {
    width: 100%;
    height: auto;
    display: block;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    border-color: var(--border-focus);
  }
}

.state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-faint);
  font-size: 14px;
}

.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(6px);
}

.preview-img {
  max-width: 92vw;
  max-height: 88vh;
  object-fit: contain;
  border-radius: 4px;
}

.preview-close {
  position: absolute;
  top: 20px;
  right: 28px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 28px;
  cursor: pointer;
  line-height: 1;
  padding: 4px;
  transition: color 0.2s;

  &:hover {
    color: var(--text-primary);
  }
}

.preview-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  font-size: 36px;
  width: 48px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: var(--text-primary);
  }

  &.prev { left: 20px; }
  &.next { right: 20px; }
}

.preview-counter {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.5);
  padding: 4px 12px;
  border-radius: 4px;
}

@media (max-width: 1200px) {
  .masonry {
    column-count: 2;
  }
}

@media (max-width: 700px) {
  .masonry {
    column-count: 1;
  }
}
</style>
