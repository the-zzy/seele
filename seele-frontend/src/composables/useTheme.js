import { ref, watch } from 'vue'
import { getItem, setItem } from '@/utils/storage'

const STORAGE_KEY = 'seele-theme'

const theme = ref(getItem(STORAGE_KEY, { versioned: false }) || 'dark')

function applyTheme (val) {
  document.documentElement.setAttribute('data-theme', val)
  setItem(STORAGE_KEY, val, { versioned: false })
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
