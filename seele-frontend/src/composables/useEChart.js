import { shallowRef, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

export function useEChart () {
  const chartRef = shallowRef(null)
  const instance = shallowRef(null)

  function init (option) {
    dispose()
    if (!chartRef.value) return
    instance.value = echarts.init(chartRef.value, null, { renderer: 'canvas' })
    instance.value.setOption(option)
    return instance.value
  }

  function dispose () {
    if (instance.value) {
      instance.value.dispose()
      instance.value = null
    }
  }

  function resize () {
    instance.value?.resize()
  }

  onMounted(() => {
    window.addEventListener('resize', resize)
  })

  onUnmounted(() => {
    dispose()
    window.removeEventListener('resize', resize)
  })

  return {
    chartRef,
    instance,
    init,
    dispose,
    resize
  }
}
