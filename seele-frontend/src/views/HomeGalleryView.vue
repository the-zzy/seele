<template>
  <div class="home-gallery">
    <div class="home-topbar">
      <div class="home-brand">Seele</div>
      <div class="home-actions">
        <button v-if="!loggedIn" class="home-btn primary" @click="$emit('open-auth')">
          登录
        </button>
        <template v-else>
          <button class="home-btn primary" @click="$emit('enter-workspace')">
            进入选股工作台
          </button>
          <button class="home-btn ghost" @click="$emit('logout')">
            退出
          </button>
        </template>
      </div>
    </div>

    <div v-if="loading" class="home-state">加载中…</div>
    <div v-else-if="images.length === 0" class="home-state">暂无图片</div>
    <div v-else class="home-masonry">
      <div
        v-for="img in images"
        :key="img.id"
        class="home-item"
        @click="openPreview(img)"
      >
        <img :src="img.url_path + '?imageView2/2/w/600'" :alt="img.original_name" loading="lazy">
      </div>
    </div>

    <!-- 预览 -->
    <div v-if="preview" class="home-preview" @click.self="closePreview">
      <button class="preview-close" @click="closePreview">✕</button>
      <button v-if="previewIndex > 0" class="preview-nav prev" @click="goPrev">‹</button>
      <button v-if="previewIndex < images.length - 1" class="preview-nav next" @click="goNext">›</button>
      <img :src="preview.url_path + '?imageView2/2/w/1200'" class="preview-img" @click.stop>
      <div class="preview-counter">{{ previewIndex + 1 }} / {{ images.length }}</div>
    </div>

    <!-- 备案号 -->
    <div class="beian-bar">
      <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">桂ICP备2023008226号-1</a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { galleryApi } from '@/api/gallery'

defineProps({
  loggedIn: { type: Boolean, default: false }
})

defineEmits(['open-auth', 'enter-workspace', 'logout'])

const images = ref([])
const loading = ref(true)
const preview = ref(null)

const previewIndex = computed(() => {
  if (!preview.value) return -1
  return images.value.indexOf(preview.value)
})

async function loadImages () {
  try {
    images.value = await galleryApi.getList()
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
.home-gallery {
  position: fixed;
  inset: 0;
  background: var(--bg-primary);
  overflow-y: auto;
  z-index: 1;
}

.home-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 100%);
  pointer-events: none;

  > * {
    pointer-events: auto;
  }
}

.home-brand {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0,0,0,0.5);
  letter-spacing: -0.01em;
}

.home-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.home-btn {
  padding: 8px 18px;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;

  &.primary {
    background: var(--accent);
    color: #fff;

    &:hover {
      opacity: 0.9;
      transform: translateY(-1px);
    }
  }

  &.ghost {
    background: rgba(255,255,255,0.1);
    color: #fff;
    border: 1px solid rgba(255,255,255,0.2);
    backdrop-filter: blur(4px);

    &:hover {
      background: rgba(255,255,255,0.18);
    }
  }
}

.home-masonry {
  column-count: 3;
  column-gap: 6px;
  padding: 6px;
  padding-top: 0;
}

.home-item {
  break-inside: avoid;
  margin-bottom: 6px;
  border-radius: 4px;
  overflow: hidden;
  cursor: zoom-in;
  transition: transform 0.15s ease, box-shadow 0.15s ease;

  img {
    width: 100%;
    height: auto;
    display: block;
  }

  &:hover {
    transform: scale(1.01);
    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
  }
}

.home-state {
  text-align: center;
  padding: 120px 20px;
  color: var(--text-faint);
  font-size: 14px;
}

.home-preview {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0,0,0,0.92);
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
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
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
    background: rgba(255,255,255,0.12);
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
  background: rgba(0,0,0,0.5);
  padding: 4px 12px;
  border-radius: 4px;
}

@media (max-width: 1200px) {
  .home-masonry {
    column-count: 2;
  }
}

@media (max-width: 700px) {
  .home-masonry {
    column-count: 1;
  }
}

.beian-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  text-align: center;
  padding: 8px 0;
  font-size: 12px;
  color: var(--text-faint);
  background: linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 100%);
  pointer-events: none;

  a {
    color: var(--text-faint);
    text-decoration: none;
    pointer-events: auto;
    transition: color 0.2s;

    &:hover {
      color: var(--text-secondary);
    }
  }
}
</style>
