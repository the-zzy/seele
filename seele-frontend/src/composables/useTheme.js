import { ref, watch } from 'vue'

const STORAGE_KEY = 'seele-theme'

const theme = ref(localStorage.getItem(STORAGE_KEY) || 'dark')

function applyTheme (val) {
  document.documentElement.setAttribute('data-theme', val)
  localStorage.setItem(STORAGE_KEY, val)
}

applyTheme(theme.value)

export function useTheme () {
  function toggle () {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  watch(theme, applyTheme)

  return {
    theme,
    toggle
  }
}
