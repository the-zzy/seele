import { computed, unref } from 'vue'

export function useFixedRows (listSource, { count = 10 } = {}) {
  return computed(() => {
    const raw = typeof listSource === 'function' ? listSource() : unref(listSource)
    const source = Array.isArray(raw) ? raw : []
    const result = [...source]
    while (result.length < count) {
      result.push(null)
    }
    return result
  })
}
