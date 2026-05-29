<template>
  <HomeGalleryView
    v-if="!workspaceMode"
    :logged-in="loggedIn"
    @open-auth="openAuth"
    @enter-workspace="enterWorkspace"
    @logout="handleLogout"
  />

  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="masthead">
        <div class="wordmark">Seele</div>
        <div class="masthead-meta">
          <span>选股工作台</span>
          <span class="dot">·</span>
          <span>{{ year }}</span>
          <span class="dot">·</span>
          <span class="version">v2.0</span>
        </div>
      </div>

      <div class="rule" />

      <nav class="nav-menu">
        <template v-for="(item, idx) in navItems" :key="item.key || item.path">
          <!-- 单项 -->
          <router-link
            v-if="item.type === 'single'"
            :to="item.path"
            class="nav-single"
            active-class="active"
          >
            <span class="num">{{ pad(idx + 1) }}</span>
            <span class="single-body">
              <span class="single-title">{{ item.name }}</span>
              <span v-if="item.section" class="single-section">{{ item.section }}</span>
            </span>
            <span class="indicator" />
          </router-link>

          <!-- 分组 -->
          <div v-else class="nav-group" :class="{ active: item.isActive }">
            <div class="group-head">
              <span class="num">{{ pad(idx + 1) }}</span>
              <span class="group-title">{{ item.name }}</span>
            </div>
            <div class="group-children">
              <router-link
                v-for="(child, cidx) in item.children"
                :key="child.path"
                :to="child.path"
                class="group-child"
                active-class="active"
              >
                <span class="child-num">{{ pad(idx + 1) }}.{{ cidx + 1 }}</span>
                <span class="child-title">{{ child.name }}</span>
              </router-link>
            </div>
          </div>
        </template>
      </nav>

      <div class="masthead-footer">
        <span class="footer-label">v2.0</span>
        <span class="footer-edition">Internal · 数据来源 Tushare</span>
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener"
          class="beian-link"
        >桂ICP备2023008226号-1</a>
        <button class="logout-btn-inline" @click="exitWorkspace">退出工作台</button>
      </div>
    </aside>

    <main class="main-content">
      <header class="top-bar">
        <div class="breadcrumb">
          <span class="crumb-section">{{ currentSection }}</span>
          <span v-if="currentTitle" class="crumb-divider">/</span>
          <span class="crumb-page">{{ currentTitle }}</span>
        </div>
        <div class="top-actions">
          <button class="theme-toggle" @click="toggleTheme">
            <span v-if="theme === 'dark'">☀</span>
            <span v-else>☾</span>
          </button>
          <button class="logout-btn" @click="exitWorkspace">退出工作台</button>
        </div>
      </header>
      <div class="page-content">
        <router-view />
      </div>
    </main>

    <AgentFloatingWidget />
    <ToastContainer />
  </div>

  <AuthModal v-model:visible="showAuthModal" @success="onLoginSuccess" />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { isLoggedIn, removeToken, onAuthRequired } from '@/utils/auth'
import { visitorApi } from '@/api/visitor'
import AgentFloatingWidget from '@/components/agent/AgentFloatingWidget.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'
import AuthModal from '@/components/auth/AuthModal.vue'
import HomeGalleryView from '@/views/HomeGalleryView.vue'

const router = useRouter()
const route = useRoute()
const { theme, toggle: toggleTheme } = useTheme()

const WORKSPACE_KEY = 'seele_workspace'

const workspaceMode = ref(localStorage.getItem(WORKSPACE_KEY) === '1')
const showAuthModal = ref(false)
const loggedIn = ref(isLoggedIn())

const year = new Date().getFullYear()

function openAuth () {
  showAuthModal.value = true
}

function onLoginSuccess () {
  loggedIn.value = true
  showAuthModal.value = false
}

function enterWorkspace () {
  workspaceMode.value = true
  localStorage.setItem(WORKSPACE_KEY, '1')
  router.push('/stock-basic')
}

function exitWorkspace () {
  workspaceMode.value = false
  localStorage.removeItem(WORKSPACE_KEY)
  router.push('/')
}

function handleLogout () {
  removeToken()
  loggedIn.value = false
}

onMounted(() => {
  onAuthRequired(() => {
    showAuthModal.value = true
  })

  // 上报访客信息
  const screenW = window.screen?.width || 0
  const screenH = window.screen?.height || 0
  visitorApi.track({
    path: window.location.href,
    screen_resolution: screenW && screenH ? `${screenW}x${screenH}` : null,
    language: navigator.language || null,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
    platform: navigator.platform || null,
    referrer: document.referrer || null
  }).catch(() => {})
})

function pad (n) {
  return String(n).padStart(2, '0')
}

const navItems = computed(() => {
  const routes = router
    .getRoutes()
    .filter((r) => r.meta?.nav)
    .sort((a, b) => (a.meta.navOrder || 99) - (b.meta.navOrder || 99))

  const result = []
  const groupMap = new Map()

  for (const r of routes) {
    if (r.meta.group) {
      if (!groupMap.has(r.meta.group)) {
        const g = {
          type: 'group',
          key: r.meta.group,
          name: r.meta.group,
          children: [],
          firstOrder: r.meta.navOrder || 99
        }
        groupMap.set(r.meta.group, g)
        result.push(g)
      }
      groupMap.get(r.meta.group).children.push({
        path: r.path,
        name: r.meta.title || r.name
      })
    } else {
      result.push({
        type: 'single',
        path: r.path,
        name: r.meta.title || r.name,
        section: r.meta.section,
        order: r.meta.navOrder || 99
      })
    }
  }

  for (const item of result) {
    if (item.type === 'group') {
      item.isActive = item.children.some((c) => c.path === route.path)
    }
  }

  return result
})

const currentTitle = computed(() => route.meta?.title || '')
const currentSection = computed(() => {
  const m = route.meta || {}
  return m.group || m.section || 'Seele'
})
</script>

<style lang="scss">
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
}

#app {
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-primary);
  height: 100%;
}

.app-layout {
  display: flex;
  height: 100%;

  .sidebar {
    width: 232px;
    flex-shrink: 0;
    background: var(--bg-primary);
    border-right: 1px solid var(--rule);
    color: var(--text-primary);
    display: flex;
    flex-direction: column;
    position: relative;

    /* 报刊感的纸张暗纹 */
    &::before {
      content: '';
      position: absolute;
      inset: 0;
      pointer-events: none;
      background-image:
        radial-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px);
      background-size: 3px 3px;
      opacity: 0.6;
    }
  }

  .masthead {
    padding: 26px 24px 18px;
    position: relative;
    z-index: 1;

    .wordmark {
      font-family: var(--font-display);
      font-weight: 600;
      font-size: 28px;
      line-height: 1;
      letter-spacing: -0.01em;
      color: var(--text-primary);
    }

    .masthead-meta {
      margin-top: 10px;
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-faint);
      display: flex;
      align-items: center;
      gap: 6px;

      .dot {
        opacity: 0.5;
      }

      .version {
        color: var(--accent);
        font-weight: 600;
      }
    }
  }

  .rule {
    height: 1px;
    margin: 0 24px;
    background: var(--rule);
    position: relative;
    z-index: 1;
  }

  .nav-menu {
    display: flex;
    flex-direction: column;
    padding: 18px 18px 24px;
    gap: 4px;
    flex: 1;
    overflow-y: auto;
    position: relative;
    z-index: 1;
  }

  .nav-single {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 10px 8px;
    text-decoration: none;
    color: var(--text-secondary);
    border-radius: 4px;
    transition: color 0.18s ease, background 0.18s ease;
    position: relative;

    .num {
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.08em;
      color: var(--text-faint);
      width: 22px;
      flex-shrink: 0;
    }

    .single-body {
      display: flex;
      flex-direction: column;
      gap: 2px;
      flex: 1;
    }

    .single-title {
      font-family: var(--font-display);
      font-weight: 600;
      font-size: 14px;
      letter-spacing: 0;
      line-height: 1.3;
    }

    .single-section {
      font-family: var(--font-mono);
      font-size: 9px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--text-faint);
    }

    .indicator {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: transparent;
      transition: background 0.18s ease;
    }

    &:hover {
      color: var(--text-primary);

      .num {
        color: var(--text-secondary);
      }
    }

    &.active {
      color: var(--text-primary);

      .num {
        color: var(--accent);
      }

      .indicator {
        background: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-subtle);
      }
    }
  }

  .nav-group {
    margin-top: 14px;

    &:first-child {
      margin-top: 0;
    }

    .group-head {
      display: flex;
      align-items: baseline;
      gap: 12px;
      padding: 8px 8px 6px;

      .num {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.08em;
        color: var(--text-faint);
        width: 22px;
        flex-shrink: 0;
      }

      .group-title {
        font-family: var(--font-display);
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.02em;
        color: var(--text-secondary);
      }
    }

    &.active .group-head {
      .num {
        color: var(--accent);
      }

      .group-title {
        color: var(--text-primary);
      }
    }

    .group-children {
      position: relative;
      padding-left: 30px;
      margin-top: 2px;

      &::before {
        content: '';
        position: absolute;
        left: 18px;
        top: 6px;
        bottom: 6px;
        width: 1px;
        background: var(--rule);
      }
    }

    .group-child {
      display: flex;
      align-items: baseline;
      gap: 10px;
      padding: 7px 10px;
      text-decoration: none;
      color: var(--text-muted);
      border-radius: 4px;
      transition: color 0.18s ease;
      position: relative;

      &::before {
        content: '';
        position: absolute;
        left: -12px;
        top: 50%;
        width: 8px;
        height: 1px;
        background: var(--rule);
      }

      .child-num {
        font-family: var(--font-mono);
        font-size: 9px;
        letter-spacing: 0.06em;
        color: var(--text-faint);
        flex-shrink: 0;
      }

      .child-title {
        font-family: var(--font-body);
        font-size: 13px;
        font-weight: 400;
        letter-spacing: -0.005em;
      }

      &:hover {
        color: var(--text-primary);

        .child-num {
          color: var(--text-secondary);
        }
      }

      &.active {
        color: var(--text-primary);
        background: var(--accent-subtle);

        .child-num {
          color: var(--accent);
        }

        .child-title {
          font-weight: 500;
        }
      }
    }
  }

  .masthead-footer {
    padding: 14px 24px 20px;
    border-top: 1px solid var(--rule);
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: relative;
    z-index: 1;

    .footer-label {
      font-family: var(--font-mono);
      font-size: 9px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-faint);
    }

    .footer-edition {
      font-family: var(--font-body);
      font-size: 11px;
      color: var(--text-muted);
    }

    .beian-link {
      font-family: var(--font-body);
      font-size: 10px;
      color: var(--text-faint);
      text-decoration: none;
      margin-top: 4px;
      transition: color 0.2s;

      &:hover {
        color: var(--text-secondary);
      }
    }

    .login-btn-inline {
      margin-top: 10px;
      width: 100%;
      padding: 7px;
      background: transparent;
      border: 1px solid var(--accent);
      border-radius: 4px;
      color: var(--accent);
      font-family: var(--font-body);
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: var(--accent);
        color: #fff;
      }
    }
  }

  .main-content {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
  }

  .top-bar {
    height: 52px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 28px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--rule);
  }

  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);

    .crumb-section {
      color: var(--text-faint);
    }

    .crumb-divider {
      color: var(--text-faint);
      opacity: 0.5;
    }

    .crumb-page {
      color: var(--text-secondary);
      font-weight: 500;
    }
  }

  .top-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .theme-toggle {
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    color: var(--text-secondary);
    transition: all 0.2s;

    &:hover {
      border-color: var(--text-faint);
      color: var(--text-primary);
    }
  }

  .logout-btn {
    background: transparent;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 6px 14px;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: 12px;
    color: var(--text-muted);
    transition: all 0.2s;

    &:hover {
      border-color: var(--down);
      color: var(--down);
    }
  }

  .page-content {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
}

@media (max-width: 1200px) {
  .app-layout {
    .sidebar {
      width: 190px;
    }

    .masthead {
      padding: 20px 16px 14px;
    }

    .nav-menu {
      padding: 14px 12px 20px;
    }

    .masthead-footer {
      padding: 12px 16px 16px;
    }
  }
}

@media (max-width: 900px) {
  .app-layout {
    .sidebar {
      width: 64px;

      .masthead {
        padding: 16px 8px;

        .wordmark {
          font-size: 18px;
          text-align: center;
        }

        .masthead-meta {
          display: none;
        }
      }

      .rule {
        margin: 0 12px;
      }

      .nav-menu {
        padding: 12px 8px;
      }

      .nav-single {
        justify-content: center;
        padding: 10px 4px;
        gap: 0;

        .num {
          display: none;
        }

        .single-body {
          display: none;
        }

        .indicator {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
        }
      }

      .nav-group {
        display: none;
      }

      .masthead-footer {
        display: none;
      }
    }

    .top-bar {
      padding: 0 18px;
    }
  }
}
</style>
