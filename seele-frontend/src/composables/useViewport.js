import { ref, computed, onMounted, onUnmounted } from 'vue'

const BREAKPOINTS = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1400
}

const ORDER = ['xs', 'sm', 'md', 'lg', 'xl', 'xxl']

function getBreakpoint () {
  const width = window.innerWidth
  let active = 'xs'
  for (const key of ORDER) {
    if (width >= BREAKPOINTS[key]) {
      active = key
    }
  }
  return active
}

const breakpoint = ref('md')
const isTouch = ref(false)

export function useViewport () {
  function update () {
    breakpoint.value = getBreakpoint()
    isTouch.value = 'ontouchstart' in window || navigator.maxTouchPoints > 0
  }

  let mql = null

  onMounted(() => {
    update()
    mql = window.matchMedia('(max-width: 767px)')
    if (mql.addEventListener) {
      mql.addEventListener('change', update)
    } else if (mql.addListener) {
      mql.addListener(update)
    }
    window.addEventListener('resize', update)
  })

  onUnmounted(() => {
    if (mql) {
      if (mql.removeEventListener) {
        mql.removeEventListener('change', update)
      } else if (mql.removeListener) {
        mql.removeListener(update)
      }
    }
    window.removeEventListener('resize', update)
  })

  const isMobile = computed(() => breakpoint.value === 'xs' || breakpoint.value === 'sm')
  const isTablet = computed(() => breakpoint.value === 'md')
  const isDesktop = computed(() => breakpoint.value === 'lg' || breakpoint.value === 'xl' || breakpoint.value === 'xxl')

  return {
    breakpoint,
    isMobile,
    isTablet,
    isDesktop,
    isTouch
  }
}
