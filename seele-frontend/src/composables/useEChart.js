import { shallowRef, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

export function useEChart () {
  const chartRef = shallowRef(null)
  const instance = shallowRef(null)
  let resizeObserver = null

  function init (option) {
    dispose()
    if (!chartRef.value) return
    instance.value = echarts.init(chartRef.value, null, { renderer: 'canvas' })
    instance.value.setOption(option)

    // ResizeObserver 自动监听容器尺寸变化，解决 flex 布局未稳定时的渲染问题
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        instance.value?.resize()
      })
      resizeObserver.observe(chartRef.value)
    }

    return instance.value
  }

  function dispose () {
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
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
