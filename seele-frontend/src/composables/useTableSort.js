import { ref } from 'vue'

export function useTableSort (options = {}) {
  const {
    defaultField = 'symbol',
    defaultOrder = 'asc',
    getDefaultOrder = null,
    onChange = null
  } = options

  const sortField = ref(defaultField)
  const sortOrder = ref(defaultOrder)

  function handleSort (field) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = getDefaultOrder ? getDefaultOrder(field) : 'asc'
    }
    if (onChange) onChange(sortField.value, sortOrder.value)
  }

  function resetSort () {
    sortField.value = defaultField
    sortOrder.value = defaultOrder
  }

  function getSortIcon (field) {
    if (field !== sortField.value) return '⇅'
    return sortOrder.value === 'asc' ? '▲' : '▼'
  }

  return {
    sortField,
    sortOrder,
    handleSort,
    resetSort,
    getSortIcon
  }
}
