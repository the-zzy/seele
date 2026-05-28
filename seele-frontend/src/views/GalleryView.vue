<template>
  <div class="gallery-view">
    <div class="gallery-header">
      <div>
        <h1 class="gallery-title">图库管理</h1>
        <span class="gallery-subtitle">共 {{ images.length }} 张图片</span>
      </div>
      <div class="header-actions">
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          multiple
          class="hidden-input"
          @change="handleFileChange"
        >
        <button class="btn-upload" :disabled="uploading" @click="triggerFileSelect">
          <span v-if="uploading">上传中 {{ uploadProgress }}%</span>
          <span v-else>+ 上传图片</span>
        </button>
      </div>
    </div>

    <div
      class="drop-zone"
      :class="{ active: dragOver }"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="handleDrop"
    >
      <div v-if="loading" class="state">加载中…</div>
      <div v-else-if="images.length === 0" class="state empty">
        <p>暂无图片</p>
        <p class="hint">拖拽图片到此处，或点击右上角上传</p>
      </div>
      <div v-else class="image-grid">
        <div
          v-for="img in images"
          :key="img.id"
          class="image-card"
        >
          <div class="image-thumb" @click="openPreview(img)">
            <img :src="img.url_path" :alt="img.original_name" loading="lazy">
          </div>
          <div class="image-info">
            <div class="image-name" :title="img.original_name">{{ img.original_name }}</div>
            <div class="image-meta">
              <span>{{ formatSize(img.file_size) }}</span>
              <span>{{ formatDate(img.created_at) }}</span>
            </div>
          </div>
          <button class="btn-delete" title="删除" @click="handleDelete(img)">
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 预览 -->
    <div v-if="preview" class="preview-overlay" @click.self="closePreview">
      <button class="preview-close" @click="closePreview">✕</button>
      <img :src="preview.url_path" class="preview-img" @click.stop>
      <div class="preview-name">{{ preview.original_name }}</div>
    </div>

    <!-- 删除确认 -->
    <div v-if="deleteTarget" class="confirm-overlay" @click.self="cancelDelete">
      <div class="confirm-dialog">
        <p>确定删除「{{ deleteTarget.original_name }}」？</p>
        <div class="confirm-actions">
          <button class="btn-ghost" @click="cancelDelete">取消</button>
          <button class="btn-danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? '删除中…' : '确定删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { galleryApi } from '@/api/gallery'
import { useToast } from '@/composables/useToast'

const toast = useToast()

const images = ref([])
const loading = ref(true)
const uploading = ref(false)
const uploadProgress = ref(0)
const dragOver = ref(false)
const preview = ref(null)
const deleteTarget = ref(null)
const deleting = ref(false)
const fileInput = ref(null)

function formatSize (bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate (str) {
  if (!str) return ''
  const d = new Date(str)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function loadImages () {
  loading.value = true
  try {
    images.value = await galleryApi.getList()
  } catch (err) {
    toast.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function triggerFileSelect () {
  fileInput.value?.click()
}

async function uploadFiles (files) {
  const validFiles = Array.from(files).filter(f => f.type.startsWith('image/'))
  if (validFiles.length === 0) {
    toast.error('请选择图片文件')
    return
  }
  uploading.value = true
  uploadProgress.value = 0
  try {
    for (const file of validFiles) {
      await galleryApi.upload(file, (percent) => {
        uploadProgress.value = percent
      })
    }
    toast.success('上传成功')
    await loadImages()
  } catch (err) {
    toast.error(err.message || '上传失败')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    if (fileInput.value) fileInput.value.value = ''
  }
}

function handleFileChange (e) {
  uploadFiles(e.target.files)
}

function handleDrop (e) {
  dragOver.value = false
  uploadFiles(e.dataTransfer.files)
}

function openPreview (img) {
  preview.value = img
}

function closePreview () {
  preview.value = null
}

function handleDelete (img) {
  deleteTarget.value = img
}

function cancelDelete () {
  deleteTarget.value = null
}

async function confirmDelete () {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await galleryApi.delete(deleteTarget.value.id)
    toast.success('删除成功')
    images.value = images.value.filter(i => i.id !== deleteTarget.value.id)
    deleteTarget.value = null
  } catch (err) {
    toast.error(err.message || '删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadImages()
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
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;

  .gallery-title {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    letter-spacing: -0.02em;
  }

  .gallery-subtitle {
    display: block;
    margin-top: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-faint);
    letter-spacing: 0.1em;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hidden-input {
  display: none;
}

.btn-upload {
  padding: 8px 18px;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  background: var(--accent);
  color: #fff;

  &:hover:not(:disabled) {
    opacity: 0.9;
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.drop-zone {
  min-height: 300px;
  border: 2px dashed transparent;
  border-radius: 8px;
  transition: border-color 0.2s, background 0.2s;

  &.active {
    border-color: var(--accent);
    background: var(--accent-subtle);
  }
}

.state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-faint);
  font-size: 14px;

  .hint {
    font-size: 12px;
    margin-top: 8px;
    color: var(--text-muted);
  }
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.image-card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.15s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
}

.image-thumb {
  aspect-ratio: 16 / 10;
  overflow: hidden;
  cursor: zoom-in;
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.image-info {
  padding: 10px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;

  .image-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .image-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
  }
}

.btn-delete {
  margin: 0 12px 10px;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--rule);
  background: transparent;
  color: var(--text-muted);

  &:hover {
    border-color: var(--down);
    color: var(--down);
  }
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
  max-height: 85vh;
  object-fit: contain;
  border-radius: 4px;
}

.preview-name {
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

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.confirm-dialog {
  background: var(--bg-secondary);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 24px 28px;
  min-width: 280px;

  p {
    margin: 0 0 20px;
    font-size: 14px;
    color: var(--text-primary);
    text-align: center;
  }
}

.confirm-actions {
  display: flex;
  justify-content: center;
  gap: 12px;

  button {
    padding: 7px 18px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid var(--rule);
    background: transparent;
    color: var(--text-secondary);

    &:hover:not(:disabled) {
      border-color: var(--text-faint);
      color: var(--text-primary);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  .btn-danger {
    border-color: var(--down);
    color: var(--down);

    &:hover:not(:disabled) {
      background: var(--down);
      color: #fff;
    }
  }
}
</style>
