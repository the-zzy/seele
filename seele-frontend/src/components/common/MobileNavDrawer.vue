<template>
  <Popup
    v-model:show="visible"
    position="left"
    class="mobile-nav-drawer"
    :style="{ width: '78%', maxWidth: '320px' }"
    overlay
    close-on-click-overlay
    lock-scroll
  >
    <div class="drawer-header">
      <span class="drawer-wordmark">Seele</span>
      <button class="drawer-close" @click="close">
        <span>✕</span>
      </button>
    </div>

    <div class="drawer-body">
      <template v-for="item in items" :key="item.key || item.path">
        <!-- 单项 -->
        <router-link
          v-if="item.type === 'single'"
          :to="item.path"
          class="drawer-link"
          :class="{ active: route.path === item.path }"
          @click="close"
        >
          <span class="link-title">{{ item.name }}</span>
          <span v-if="item.section" class="link-meta">{{ item.section }}</span>
        </router-link>

        <!-- 分组 -->
        <div v-else class="drawer-group">
          <div class="group-head">{{ item.name }}</div>
          <router-link
            v-for="child in item.children"
            :key="child.path"
            :to="child.path"
            class="drawer-link child-link"
            :class="{ active: route.path === child.path }"
            @click="close"
          >
            <span class="link-title">{{ child.name }}</span>
          </router-link>
        </div>
      </template>
    </div>
  </Popup>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Popup } from 'vant'

const props = defineProps({
  modelValue: Boolean,
  items: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const route = useRoute()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

function close () {
  visible.value = false
}
</script>

<style scoped lang="scss">
.mobile-nav-drawer {
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px var(--page-pad-x);
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;
}

.drawer-wordmark {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.drawer-close {
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &:hover {
    border-color: var(--text-faint);
    color: var(--text-primary);
  }
}

.drawer-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 0;
}

.drawer-group {
  margin-bottom: 18px;

  &:last-child {
    margin-bottom: 0;
  }
}

.group-head {
  padding: 10px var(--page-pad-x) 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.drawer-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px var(--page-pad-x);
  text-decoration: none;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 500;
  line-height: 1.3;
  transition: color 0.15s, background 0.15s;
  position: relative;

  &.child-link {
    padding-left: calc(var(--page-pad-x) + 14px);
    font-size: 14px;
    font-weight: 400;
    color: var(--text-muted);
  }

  &.active {
    color: var(--text-primary);
    background: var(--accent-subtle);

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 8px;
      bottom: 8px;
      width: 3px;
      background: var(--accent);
      border-radius: 0 3px 3px 0;
    }
  }

  &:active {
    background: var(--bg-tertiary);
  }
}

.link-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-faint);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}
</style>
